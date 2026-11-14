"""Fixed recording coordinator1; it never certifies result acceptance or reap.

The parent concurrently drains this and native2. A receive timestamp is only a
diagnostic: acceptance belongs after the runtime's original artifact validation.
No caller-selected callbacks, commands, paths or validators run in this channel.
"""
import asyncio
from collections import deque
from dataclasses import dataclass
import errno
import os
import socket
import struct
import time

from .recording_artifacts import _finish
from .recording_native_schema import decode, keys, integer, sha, identifier
from .recording_runtime_artifacts import _line, validate_ref, _text

ENV_FD = 'GAMST_RECORDING_RUNTIME_FD_V1'
MAX_FRAME = 65536
MAX_QUEUE_FRAMES = 64
MAX_QUEUE_BYTES = 1024**2
_ISSUER = object()


class CoordinatorError(ValueError):
    pass


def _clock(value):
    _text(value,256)
    if any(not 32<=ord(c)<=126 for c in value):raise ValueError('printable actual clock implementation required')


def validate_bootstrap(value):
    keys(value,('schema_version','type','nonce','invocation_ordinal','execution_sha256',
        'runtime_policy_sha256','latency_policy_sha256','clock_domain','startup_deadline_ns','run_deadline_ns'))
    if type(value['schema_version']) is not int or value['schema_version']!=1 or value['type']!='runtime_bootstrap':raise ValueError('coordinator bootstrap1 required')
    for name in ('nonce','execution_sha256','runtime_policy_sha256','latency_policy_sha256'):sha(value[name])
    integer(value['invocation_ordinal'],0,95);identifier(value['clock_domain'])
    integer(value['startup_deadline_ns'],1);integer(value['run_deadline_ns'],value['startup_deadline_ns'])
    return value


def validate_frame(value, *, direction, bootstrap, sequence):
    keys(value,('schema_version','type','nonce','sequence','fields'))
    if type(value['schema_version']) is not int or value['schema_version']!=1 or value['nonce']!=bootstrap['nonce'] or integer(value['sequence'])!=sequence:
        raise ValueError('coordinator version/nonce/contiguous sequence mismatch')
    typ=value['type'];f=value['fields']
    if direction=='parent':
        if typ=='start':keys(f,('execution_sha256','clock_domain'))
        elif typ=='cancel':
            keys(f,('reason',))
            if f['reason'] not in ('deadline','parent_shutdown','protocol_failed','capacity_exhausted'):raise ValueError('fixed cancel reason required')
        else:raise ValueError('unknown parent coordinator frame')
    elif typ=='ready':
        keys(f,('execution_sha256','asset_inventory_sha256','clock_domain','clock_implementation'))
        sha(f['asset_inventory_sha256']);_clock(f['clock_implementation'])
    elif typ=='playback_started':
        keys(f,('execution_sha256','mapping','mapping_sha256','source_mappings','source_mappings_sha256','anchor_monotonic_ns','clock_domain'))
        validate_ref(f['mapping']);validate_ref(f['source_mappings'])
        sha(f['mapping_sha256']);sha(f['source_mappings_sha256']);integer(f['anchor_monotonic_ns'])
        if f['mapping']['path']!='mapping.json' or f['source_mappings']['path']!='source-mappings.json':raise ValueError('fixed original mapping artifacts required')
    elif typ=='answer_ready':
        keys(f,('task_id','result','result_sha256'));identifier(f['task_id']);validate_ref(f['result']);sha(f['result_sha256'])
        path=f['result']['path']
        if not path.startswith('tasks/task-') or not path.endswith('-result.json') or f['result_sha256']!=f['result']['file_sha256']:raise ValueError('fixed sealed task result digest required')
    elif typ=='runtime_terminal':
        keys(f,('execution_sha256','child_summary','child_summary_sha256'));validate_ref(f['child_summary']);sha(f['child_summary_sha256'])
        if f['child_summary']['path']!='child-summary.json' or f['child_summary']['file_sha256']!=f['child_summary_sha256']:raise ValueError('fixed sealed child summary digest required')
    else:raise ValueError('unknown child coordinator frame')
    if 'execution_sha256' in f and f['execution_sha256']!=bootstrap['execution_sha256']:raise ValueError('coordinator original execution mismatch')
    if 'clock_domain' in f and f['clock_domain']!=bootstrap['clock_domain']:raise ValueError('coordinator clock domain mismatch')
    _line(value,MAX_FRAME)
    return value


@dataclass(frozen=True,init=False)
class ReceivedFrame:
    _bytes: bytes
    received_ns: int

    def __init__(self,data,received_ns,*,_issuer=None):
        if _issuer is not _ISSUER:raise TypeError('coordinator must receive frame')
        object.__setattr__(self,'_bytes',data);object.__setattr__(self,'received_ns',received_ns)

    def snapshot(self):return decode(self._bytes,MAX_FRAME)


async def _until(awaitable,deadline_ns):
    remaining=(deadline_ns-time.monotonic_ns())/1e9
    if remaining<=0:
        if hasattr(awaitable,'close'):awaitable.close()
        raise TimeoutError('coordinator deadline elapsed')
    return await asyncio.wait_for(awaitable,remaining)


async def _read_exact(sock,count,deadline,*,clean_eof=False):
    data=bytearray();loop=asyncio.get_running_loop()
    while len(data)<count:
        part=await _until(loop.sock_recv(sock,count-len(data)),deadline)
        if not part:
            if clean_eof and not data:return None
            raise CoordinatorError('partial coordinator frame or unexpected EOF')
        data.extend(part)
    return bytes(data)


async def _read_packet(sock,deadline):
    header=await _read_exact(sock,4,deadline,clean_eof=True)
    if header is None:return None
    size=struct.unpack('!I',header)[0]
    if not 1<=size<=MAX_FRAME:raise CoordinatorError('coordinator frame length exceeds bound')
    data=await _read_exact(sock,size,deadline)
    return data


def _packet(value):
    data=_line(value,MAX_FRAME)
    return struct.pack('!I',len(data))+data


class _Endpoint:
    def _initialize(self,sock,bootstrap,side):
        self.socket=sock;self.socket.setblocking(False);self.socket.set_inheritable(False)
        self._bootstrap_bytes=_line(validate_bootstrap(bootstrap),MAX_FRAME)
        self.side=side;self._loop=asyncio.get_running_loop()
        self._out=deque();self._in=deque();self._write_wake=asyncio.Event();self._read_wake=asyncio.Event()
        self._stop_event=asyncio.Event()
        self._out_bytes=self._in_bytes=0;self._out_frames=0
        self._send_seq=self._receive_seq=0;self._failure=None;self._aborted=False;self._closing=False
        self._send_ready=self._receive_ready=False;self._sent_start=self._received_start=False
        self._send_playback=self._receive_playback=False;self._send_terminal=self._receive_terminal=False
        self._sent_cancel=self._received_cancel=False;self._eof=False
        self._send_tasks=set();self._receive_tasks=set();self._reader=None;self._writer=None
        self._close_task=self._abort_task=None;self._sent_frames=self._received_frames=0
        self._sent_bytes=self._received_bytes=0;self._started_ns=time.monotonic_ns()
        self.start_send_begin_ns=self.start_send_complete_ns=None
        self.ready_received_ns=self.playback_received_ns=self.anchor_monotonic_ns=None
        self._clock_implementation=None

    @property
    def bootstrap(self):return decode(self._bootstrap_bytes)

    def _start_jobs(self):
        self._writer=asyncio.create_task(self._write());self._reader=asyncio.create_task(self._read())

    def _deadline(self):
        b=self.bootstrap
        return b['run_deadline_ns'] if self._sent_start or self._received_start or self._sent_cancel or self._received_cancel else b['startup_deadline_ns']

    def _state(self,typ,fields,*,sending):
        direction=self.side if sending else ('child' if self.side=='parent' else 'parent')
        prefix='_send' if sending else '_receive'
        if direction=='parent':
            if typ=='start':
                if self._sent_start or self._received_start or self._sent_cancel or self._received_cancel or not (self._send_ready or self._receive_ready):raise CoordinatorError('START must follow READY exactly once')
                setattr(self,'_sent_start' if sending else '_received_start',True)
            else:
                flag='_sent_cancel' if sending else '_received_cancel'
                if getattr(self,flag):raise CoordinatorError('one coordinator cancellation only')
                setattr(self,flag,True)
                if not sending:self._stop_event.set()
            return
        if getattr(self,prefix+'_terminal'):raise CoordinatorError('trailing coordinator data after terminal')
        if typ=='ready':
            if getattr(self,prefix+'_ready') or getattr(self,prefix+'_playback'):raise CoordinatorError('duplicate/out-of-order READY')
            setattr(self,prefix+'_ready',True)
        elif typ=='playback_started':
            if not (self._sent_start or self._received_start) or getattr(self,prefix+'_playback'):raise CoordinatorError('playback requires one successful START')
            setattr(self,prefix+'_playback',True)
        elif typ=='answer_ready':
            if not getattr(self,prefix+'_playback'):raise CoordinatorError('task result cannot precede actual mapping')
            seen=self._send_tasks if sending else self._receive_tasks
            if fields['task_id'] in seen or len(seen)>=64:raise CoordinatorError('duplicate/excess task result')
            seen.add(fields['task_id'])
        else:setattr(self,prefix+'_terminal',True)

    def send(self,typ,fields):
        """Synchronous bounded queue admission; returned future means sent bytes."""
        if self._failure or self._closing or self._aborted:raise CoordinatorError('coordinator writer closed')
        value=dict(schema_version=1,type=typ,nonce=self.bootstrap['nonce'],sequence=self._send_seq,fields=fields)
        data=_packet(value);value=decode(data[4:]);validate_frame(value,direction=self.side,bootstrap=self.bootstrap,sequence=self._send_seq)
        if self._out_frames>=MAX_QUEUE_FRAMES or self._out_bytes+len(data)>MAX_QUEUE_BYTES:
            self._fail('overflow');raise CoordinatorError('coordinator send queue exhausted before admission')
        self._state(typ,value['fields'],sending=True)
        future=self._loop.create_future();future.add_done_callback(lambda f:None if f.cancelled() else f.exception())
        self._out.append((typ,data,future));self._out_frames+=1;self._out_bytes+=len(data);self._send_seq+=1
        self._write_wake.set();return future

    async def send_wait(self,typ,fields):
        return await asyncio.shield(self.send(typ,fields))

    async def receive(self):
        while True:
            if self._in:
                frame,size=self._in.popleft();self._in_bytes-=size
                return frame
            if self._failure:raise CoordinatorError(self._failure)
            if self._eof:return None
            self._read_wake.clear();await self._read_wake.wait()

    def _fail(self,reason):
        if self._failure is None:self._failure=reason
        self._read_wake.set();self._write_wake.set()
        # Close before cancellation; a completed wait_for write may consume
        # cancellation on Python3.10. Both loop guards also check the FD.
        self.socket.close()
        self._stop_event.set()
        current=asyncio.current_task()
        for task in (self._reader,self._writer):
            if task is not None and task is not current and not task.done():task.cancel()

    async def _read(self):
        try:
            while not self._aborted and self.socket.fileno()>=0:
                data=await _read_packet(self.socket,self._deadline())
                if data is None:
                    self._eof=True
                    if self.side=='parent' and not self._receive_terminal:raise CoordinatorError('eof_before_terminal')
                    if self.side=='child' and not self._closing:
                        self._received_cancel=True;self._stop_event.set()
                    return
                self._received_bytes+=len(data)+4;value=decode(data,MAX_FRAME)
                if _line(value,MAX_FRAME)!=data:raise CoordinatorError('canonical coordinator JSON required')
                direction='child' if self.side=='parent' else 'parent'
                validate_frame(value,direction=direction,bootstrap=self.bootstrap,sequence=self._receive_seq)
                self._state(value['type'],value['fields'],sending=False)
                stamp=time.monotonic_ns()
                if self.side=='parent':
                    if value['type']=='ready':
                        self.ready_received_ns=stamp;self._clock_implementation=value['fields']['clock_implementation']
                        if self._clock_implementation!=time.get_clock_info('monotonic').implementation:raise CoordinatorError('clock_mismatch')
                    elif value['type']=='playback_started':
                        anchor=value['fields']['anchor_monotonic_ns']
                        if self.start_send_begin_ns is None or not self.start_send_begin_ns<=anchor<=stamp:raise CoordinatorError('invalid_mapping')
                        self.playback_received_ns=stamp;self.anchor_monotonic_ns=anchor
                if len(self._in)>=MAX_QUEUE_FRAMES or self._in_bytes+len(data)+4>MAX_QUEUE_BYTES:raise CoordinatorError('overflow')
                self._in.append((ReceivedFrame(data,stamp,_issuer=_ISSUER),len(data)+4));self._in_bytes+=len(data)+4
                self._receive_seq+=1;self._received_frames+=1;self._read_wake.set()
        except asyncio.CancelledError:
            if not self._closing and not self._aborted:self._fail('cancelled')
        except (TimeoutError,asyncio.TimeoutError):self._fail('timeout')
        except Exception as exc:self._fail(str(exc) if isinstance(exc,CoordinatorError) else 'malformed')
        finally:self._read_wake.set()

    async def _write(self):
        try:
            while not self._aborted and self.socket.fileno()>=0:
                if not self._out:
                    if self._closing:
                        try:self.socket.shutdown(socket.SHUT_WR)
                        except OSError as exc:
                            if not (self.side=='parent' and self._receive_terminal and self._eof and exc.errno in (errno.ENOTCONN,errno.EPIPE)):
                                raise
                        return
                    self._write_wake.clear();await self._write_wake.wait();continue
                typ,data,future=self._out.popleft()
                try:
                    if typ=='start':self.start_send_begin_ns=time.monotonic_ns()
                    await _until(self._loop.sock_sendall(self.socket,data),self._deadline())
                    if typ=='start':self.start_send_complete_ns=time.monotonic_ns()
                    self._sent_bytes+=len(data);self._sent_frames+=1
                    if not future.done():future.set_result(time.monotonic_ns())
                except BaseException as exc:
                    if not future.done():future.set_exception(exc)
                    raise
                finally:self._out_frames-=1;self._out_bytes-=len(data)
        except asyncio.CancelledError:
            if not self._closing and not self._aborted:self._fail('cancelled')
        except (TimeoutError,asyncio.TimeoutError):self._fail('timeout')
        except Exception:self._fail('write_failed')
        finally:
            while self._out:
                _,data,future=self._out.popleft()
                if not future.done():future.set_exception(CoordinatorError('coordinator writer stopped'))
            self._out_frames=self._out_bytes=0

    async def close(self):
        if self._abort_task is not None:return await _finish(self._abort_task)
        if self._close_task is None:
            self._closing=True;self._write_wake.set();self._close_task=asyncio.create_task(self._close())
        try:await asyncio.shield(self._close_task)
        except asyncio.CancelledError:
            await _finish(self._close_task);raise

    async def _close(self):
        try:
            if self._writer is not None:await _finish(self._writer)
            if self.side=='parent' and self._reader is not None and not self._failure:
                await _finish(self._reader)
        finally:
            self.socket.close()
            if self._reader is not None and not self._reader.done():self._reader.cancel()
            if self._reader is not None:await asyncio.gather(self._reader,return_exceptions=True)
        if self.side=='child' and not self._send_terminal and self._failure is None:self._failure='eof_before_terminal'
        if self._failure:raise CoordinatorError(self._failure)

    async def abort(self):
        if self._abort_task is None:
            self._aborted=True;self._fail('cancelled');self._abort_task=asyncio.create_task(self._abort())
        try:await asyncio.shield(self._abort_task)
        except asyncio.CancelledError:
            await _finish(self._abort_task);raise

    async def _abort(self):
        self.socket.close()
        for task in (self._writer,self._reader,self._close_task):
            if task is not None and not task.done():task.cancel()
        await asyncio.gather(*(t for t in (self._writer,self._reader,self._close_task) if t is not None),return_exceptions=True)

    @property
    def stop_requested(self):return bool(self._received_cancel or self._eof or self._failure or self._aborted)

    async def wait_stop(self):
        """Runtime-owned watcher stops source/provider admission immediately."""
        await self._stop_event.wait()

    def status(self):
        return dict(failure=self._failure,sent_frames=self._sent_frames,received_frames=self._received_frames,
            sent_bytes=self._sent_bytes,received_bytes=self._received_bytes,terminal_seen=self._receive_terminal,
            eof_seen=self._eof,queued_send_frames=self._out_frames,queued_send_bytes=self._out_bytes,
            queued_receive_frames=len(self._in),queued_receive_bytes=self._in_bytes,
            acceptance_boundary_verified=False,process_reaped=False)

    def handshake(self):
        if self.side!='parent':raise ValueError('handshake evidence belongs to parent')
        b=self.bootstrap;started=all(v is not None for v in (self.ready_received_ns,self.start_send_begin_ns,self.start_send_complete_ns,self.playback_received_ns,self.anchor_monotonic_ns)) and not self._failure
        reason='completed' if started else self._failure if self._failure in ('clock_mismatch','invalid_mapping') else 'startup_timeout' if self._failure=='timeout' else 'start_write_failed' if self._failure=='write_failed' else 'protocol_failed'
        return dict(schema_version=1,kind='recording_handshake',execution_sha256=b['execution_sha256'],nonce=b['nonce'],
            clock_domain=b['clock_domain'],clock_implementation=self._clock_implementation or time.get_clock_info('monotonic').implementation,
            ready_received_ns=self.ready_received_ns,start_send_begin_ns=self.start_send_begin_ns,start_send_complete_ns=self.start_send_complete_ns,
            playback_received_ns=self.playback_received_ns,anchor_monotonic_ns=self.anchor_monotonic_ns,state='started' if started else 'failed',reason=reason)


class ParentCoordinatorChannel(_Endpoint):
    def __init__(self,bootstrap):
        bootstrap=decode(_line(validate_bootstrap(bootstrap),MAX_FRAME))
        parent,child=socket.socketpair()
        self._child=child;self._prepared=False;self._spawned=False
        self._initialize(parent,bootstrap,'parent')

    def spawn_options(self):
        if self._spawned or self._child is None:raise RuntimeError('coordinator spawn already consumed')
        fd=self._child.fileno()
        return dict(pass_fds=(fd,),env_delta={ENV_FD:str(fd)})

    async def spawned(self):
        """Call immediately after the owned spawn; closes parent's child endpoint."""
        if self._spawned:raise RuntimeError('one owned coordinator spawn required')
        self._spawned=True
        if self._child is not None:self._child.close();self._child=None
        try:
            packet=_packet(self.bootstrap)
            await _until(self._loop.sock_sendall(self.socket,packet),self.bootstrap['startup_deadline_ns'])
            self._sent_bytes+=len(packet);self._start_jobs()
        except BaseException:
            await self.abort();raise

    async def abort(self):
        if self._child is not None:self._child.close();self._child=None
        return await super().abort()

    async def close(self):
        if self._child is not None:self._child.close();self._child=None
        return await super().close()


class ChildCoordinatorChannel(_Endpoint):
    @classmethod
    async def from_environment(cls,*,startup_deadline_ns):
        """Explicit trusted original startup deadline bounds bootstrap reading."""
        integer(startup_deadline_ns,1)
        value=os.environ.get(ENV_FD)
        if type(value) is not str or not value.isascii() or not value.isdecimal():raise ValueError('owned runtime FD required')
        fd=int(value)
        if fd<3:raise ValueError('dedicated coordinator socket required')
        os.set_inheritable(fd,False)
        try:sock=socket.socket(fileno=fd)
        except BaseException:os.close(fd);raise
        sock.setblocking(False)
        try:
            data=await _read_packet(sock,startup_deadline_ns)
            if data is None:raise CoordinatorError('bootstrap EOF')
            bootstrap=validate_bootstrap(decode(data,MAX_FRAME))
            if _line(bootstrap,MAX_FRAME)!=data or bootstrap['startup_deadline_ns']!=startup_deadline_ns:raise CoordinatorError('original canonical coordinator bootstrap deadline required')
            self=cls();self._initialize(sock,bootstrap,'child');self._received_bytes=len(data)+4;self._start_jobs();return self
        except BaseException:sock.close();raise
