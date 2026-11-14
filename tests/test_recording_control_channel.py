import asyncio
import copy
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from benchmarks.recording_control_channel import (ParentCoordinatorChannel,
    ChildCoordinatorChannel,CoordinatorError,ENV_FD,validate_bootstrap,validate_frame,_packet)

H='a'*64


def bootstrap(seconds=5):
    now=time.monotonic_ns()
    return dict(schema_version=1,type='runtime_bootstrap',nonce=H,invocation_ordinal=0,
        execution_sha256=H,runtime_policy_sha256=H,latency_policy_sha256=H,
        clock_domain='host',startup_deadline_ns=now+int(seconds*1e9),run_deadline_ns=now+int(seconds*1e9))


def ref(path):return dict(path=path,file_sha256=H,bytes=1)


def ready():
    return dict(execution_sha256=H,asset_inventory_sha256=H,clock_domain='host',
        clock_implementation=time.get_clock_info('monotonic').implementation)


def playback(anchor=None):
    return dict(execution_sha256=H,mapping=ref('mapping.json'),mapping_sha256=H,
        source_mappings=ref('source-mappings.json'),source_mappings_sha256=H,
        anchor_monotonic_ns=time.monotonic_ns() if anchor is None else anchor,clock_domain='host')


def terminal():return dict(execution_sha256=H,child_summary=ref('child-summary.json'),child_summary_sha256=H)


class Coordinator(unittest.IsolatedAsyncioTestCase):
    async def pair(self,seconds=5):
        b=bootstrap(seconds);parent=ParentCoordinatorChannel(b);self.addAsyncCleanup(parent.abort)
        fd=os.dup(parent.spawn_options()['pass_fds'][0])
        with patch.dict(os.environ,{ENV_FD:str(fd)}):
            childtask=asyncio.create_task(ChildCoordinatorChannel.from_environment(startup_deadline_ns=b['startup_deadline_ns']))
            await parent.spawned();child=await childtask
        self.addAsyncCleanup(child.abort)
        return parent,child

    async def started(self):
        parent,child=await self.pair()
        await child.send_wait('ready',ready());frame=await parent.receive()
        self.assertEqual(frame.snapshot()['type'],'ready')
        await parent.send_wait('start',dict(execution_sha256=H,clock_domain='host'))
        self.assertEqual((await child.receive()).snapshot()['type'],'start')
        await child.send_wait('playback_started',playback());await parent.receive()
        return parent,child

    async def test_actual_fixed_frames_parent_clock_and_acceptance_is_not_receive(self):
        parent,child=await self.started()
        sent=await child.send_wait('answer_ready',dict(task_id='t',result=ref('tasks/task-0000-result.json'),result_sha256=H))
        frame=await parent.receive();self.assertEqual(frame.snapshot()['fields']['task_id'],'t')
        copyframe=frame.snapshot();copyframe['fields']['task_id']='changed'
        self.assertEqual(frame.snapshot()['fields']['task_id'],'t')
        self.assertGreater(frame.received_ns,0)
        self.assertFalse(parent.status()['acceptance_boundary_verified'])
        self.assertFalse(parent.status()['process_reaped'])
        await child.send_wait('runtime_terminal',terminal());await child.close()
        self.assertEqual((await parent.receive()).snapshot()['type'],'runtime_terminal')
        self.assertIsNone(await parent.receive());await parent.close()
        handshake=parent.handshake();self.assertEqual(handshake['state'],'started')
        self.assertLessEqual(handshake['start_send_begin_ns'],handshake['anchor_monotonic_ns'])
        self.assertLessEqual(handshake['anchor_monotonic_ns'],handshake['playback_received_ns'])

    async def test_live_subprocess_noninheritance_and_owned_terminal_eof(self):
        parent=ParentCoordinatorChannel(bootstrap());self.addAsyncCleanup(parent.abort)
        options=parent.spawn_options();env=dict(os.environ,**options['env_delta'])
        script='''import asyncio,os,time,sys
from benchmarks.recording_control_channel import ChildCoordinatorChannel,ENV_FD
async def run():
 c=await ChildCoordinatorChannel.from_environment(startup_deadline_ns=int(sys.argv[1]))
 assert not os.get_inheritable(int(os.environ[ENV_FD]))
 b=c.bootstrap;h=b['execution_sha256']
 def ref(p):return dict(path=p,file_sha256=h,bytes=1)
 await c.send_wait('ready',dict(execution_sha256=h,asset_inventory_sha256=h,clock_domain=b['clock_domain'],clock_implementation=time.get_clock_info('monotonic').implementation))
 assert (await c.receive()).snapshot()['type']=='start'
 await c.send_wait('playback_started',dict(execution_sha256=h,mapping=ref('mapping.json'),mapping_sha256=h,source_mappings=ref('source-mappings.json'),source_mappings_sha256=h,anchor_monotonic_ns=time.monotonic_ns(),clock_domain=b['clock_domain']))
 await c.send_wait('runtime_terminal',dict(execution_sha256=h,child_summary=ref('child-summary.json'),child_summary_sha256=h))
 await c.close()
asyncio.run(run())'''
        process=await asyncio.create_subprocess_exec(sys.executable,'-c',script,str(parent.bootstrap['startup_deadline_ns']),env=env,pass_fds=options['pass_fds'],close_fds=True,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        await parent.spawned()
        self.assertEqual((await parent.receive()).snapshot()['type'],'ready')
        await parent.send_wait('start',dict(execution_sha256=H,clock_domain='host'))
        self.assertEqual((await parent.receive()).snapshot()['type'],'playback_started')
        self.assertEqual((await parent.receive()).snapshot()['type'],'runtime_terminal')
        self.assertIsNone(await parent.receive())
        stdout,stderr=await asyncio.wait_for(process.communicate(),3)
        self.assertEqual(process.returncode,0,stderr.decode());await parent.close()

    async def test_parent_disconnect_and_cancel_stop_child_without_inventing_terminal(self):
        parent,child=await self.pair()
        await parent.send_wait('cancel',{'reason':'parent_shutdown'})
        await asyncio.wait_for(child.wait_stop(),1)
        self.assertTrue(child.stop_requested)
        self.assertEqual((await child.receive()).snapshot()['type'],'cancel')
        with self.assertRaises(CoordinatorError):parent.send('cancel',{'reason':'parent_shutdown'})
        await child.abort();await parent.abort()
        self.assertFalse(parent.status()['terminal_seen'])

    async def test_completed_handshake_survives_later_owned_abort(self):
        parent,child=await self.started()
        before=parent.handshake()
        await parent.abort()
        self.assertEqual(parent.handshake(),before)
        self.assertEqual(parent.handshake()['state'],'started')
        self.assertEqual(parent.status()['failure'],'cancelled')

    async def test_repeated_abort_closes_blocked_writer_and_joins_all_tasks(self):
        parent,child=await self.started()
        real=asyncio.get_running_loop().sock_sendall;entered=asyncio.Event()
        async def blocked(sock,data):
            if sock is child.socket:
                entered.set();await asyncio.Future()
            return await real(sock,data)
        with patch.object(asyncio.get_running_loop(),'sock_sendall',blocked):
            child.send('runtime_terminal',terminal());await entered.wait()
            closing=asyncio.create_task(child.close());await asyncio.sleep(0)
            aborting=asyncio.create_task(child.abort());await asyncio.sleep(0);aborting.cancel();await asyncio.sleep(0);aborting.cancel()
            try:await asyncio.wait_for(aborting,1)
            except asyncio.CancelledError:pass
            await asyncio.gather(closing,return_exceptions=True)
        self.assertEqual(child.socket.fileno(),-1)
        self.assertTrue(child._writer.done());self.assertTrue(child._reader.done())

    async def test_raw_duplicate_json_partial_frame_wrong_nonce_and_trailing_reject(self):
        for mode in ('duplicate','partial','nonce','trailing','oversize'):
            with self.subTest(mode=mode):
                parent,child=await self.pair()
                if mode=='trailing':
                    await child.send_wait('runtime_terminal',terminal());await parent.receive()
                    data=_packet(dict(schema_version=1,type='ready',nonce=H,sequence=1,fields=ready()))
                elif mode=='partial':data=struct.pack('!I',50)+b'{}'
                elif mode=='oversize':data=struct.pack('!I',65537)
                elif mode=='duplicate':
                    raw=b'{"schema_version":1,"schema_version":1}'
                    data=struct.pack('!I',len(raw))+raw
                else:data=_packet(dict(schema_version=1,type='ready',nonce='b'*64,sequence=0,fields=ready()))
                await asyncio.get_running_loop().sock_sendall(child.socket,data)
                if mode=='partial':child.socket.shutdown(socket.SHUT_WR)
                with self.assertRaises(CoordinatorError):await asyncio.wait_for(parent.receive(),1)
                await child.abort();await parent.abort()

    async def test_wrong_clock_and_anchor_reject_without_started_handshake(self):
        parent,child=await self.pair()
        bad=ready();bad['clock_implementation']='another clock'
        await child.send_wait('ready',bad)
        with self.assertRaises(CoordinatorError):await parent.receive()
        self.assertEqual(parent.handshake()['state'],'failed')
        parent,child=await self.pair()
        await child.send_wait('ready',ready());await parent.receive()
        await parent.send_wait('start',dict(execution_sha256=H,clock_domain='host'));await child.receive()
        await child.send_wait('playback_started',playback(0))
        with self.assertRaises(CoordinatorError):await parent.receive()
        self.assertEqual(parent.handshake()['reason'],'invalid_mapping')

    async def test_outbound_queue_budget_and_task_duplicates(self):
        parent,child=await self.started()
        for n in range(64):child.send('answer_ready',dict(task_id='t%d'%n,result=ref('tasks/task-%04d-result.json'%n),result_sha256=H))
        self.assertEqual(child.status()['queued_send_frames'],64)
        with self.assertRaises(CoordinatorError):child.send('runtime_terminal',terminal())
        await child.abort();await parent.abort()
        parent,child=await self.started()
        row=dict(task_id='same',result=ref('tasks/task-0000-result.json'),result_sha256=H)
        await child.send_wait('answer_ready',row);await parent.receive()
        with self.assertRaises(CoordinatorError):child.send('answer_ready',row)

    async def test_bootstrap_deadline_exact_bool_and_unknown_fields(self):
        for key,value in (('invocation_ordinal',True),('nonce','bad'),('startup_deadline_ns',-1),('run_deadline_ns',0)):
            b=bootstrap();b[key]=value
            with self.assertRaises(ValueError):validate_bootstrap(b)
        b=bootstrap();b['command']='arbitrary'
        with self.assertRaises(ValueError):ParentCoordinatorChannel(b)
        parent,child=await self.pair(.05)
        await asyncio.sleep(.07)
        self.assertEqual(parent.status()['failure'],'timeout')
        self.assertEqual(parent.socket.fileno(),-1)
