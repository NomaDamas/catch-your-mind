"""Explicit runtime-v2 declaration entrypoints; legacy native APIs stay strict.

These validators do not activate providers, certify assets or constitute the
owned-input admission receipt. Actual activation also requires source/asset,
clock, joint memory/artifact and fixed child transport preflight.
"""
from .recording_native_schema import (_validate_scope_protocol_common, digest,
    snapshot, keys)
from .recording_runtime_contract import validate_runtime_policy


def validate_runtime_scope_protocol(declarations, *, latency_policy, source_bundles, numeric_inputs=None):
    d=snapshot(declarations)
    if 'runtime_policy' not in d:raise ValueError('original runtime policy required')
    policy=validate_runtime_policy(d['runtime_policy'],comparison_plan=d['plan'],
        latency_policy=latency_policy,source_bundles=source_bundles)
    numeric=policy.document()['schema_version']==2
    if numeric:_validate_numeric_inputs(d,policy.document(),latency_policy,source_bundles,numeric_inputs)
    elif numeric_inputs is not None:raise ValueError('U1 rejects prospective numeric inputs')
    d=_validate_scope_protocol_common(d,runtime_profiles=True,runtime_numeric=numeric)
    c=d['collection'];u=policy.document()
    if c['runtime_policy_sha256']!=policy.sha256:
        raise ValueError('original collection must bind the validated runtime policy')
    if len(c['recordings'])!=len(u['recordings']):raise ValueError('complete original runtime recordings required')
    for original,upstream in zip(c['recordings'],u['recordings']):
        for field in ('recording_id','source_manifest_sha256','tasks_sha256','profiles_sha256'):
            if original[field]!=upstream[field]:raise ValueError('runtime recording order/identity differs from collection')
    _validate_runtime_bindings(d,u)
    return d


def _validate_runtime_bindings(d,u):
    for arm,policy in zip(d['collection']['arms'],u['arms']):
        if arm['arm']!=policy['arm']:raise ValueError('original ABC arm order required')
        bindings={b['binding_id']:b for b in arm['provider_bindings']}
        adapters={a['adapter_id']:a for a in u['adapters']}
        expected=set()
        for lane in policy['lanes']:
            bid=lane['binding_id'];expected.add(bid)
            if bid not in bindings:raise ValueError('missing original semantic provider binding')
            binding=bindings[bid];adapter=adapters[lane['adapter_id']]
            role='text_llm' if lane['role']=='text_answer' else 'strong_vlm' if lane['role']=='fill_strong' else 'small_vlm'
            boundary='process_adapter' if adapter['implementation']=='smolvlm_process_v1' else 'async_client_callback'
            if (binding['provider'],binding['model_revision'],binding['role'],binding['entry_boundary'],binding['operation_kinds']) != (
                    adapter['provider'],adapter['model_revision'],role,boundary,['semantic']):
                raise ValueError('actual semantic adapter differs from original binding')
            if binding['semantic_lane']!=policy['lanes'].index(lane):
                raise ValueError('semantic lane ordinal differs from frozen policy')
            # Adapter config identity is canonical, not a provider/model alias.
            if adapter['implementation']!='smolvlm_process_v1' and binding['config_sha256']!=digest(adapter['config']):
                raise ValueError('semantic adapter configuration digest mismatch')
        for recording in policy['recording_policies']:
            for delivery in recording['deliveries']:
                if delivery['binding_id'] is not None:expected.add(delivery['binding_id'])
            fill=recording['fill_chain']
            if fill is not None:
                # The direct fill computation binding is resolved by its fixed
                # source/backend identity, never guessed from callback timing.
                fill_bindings=[b for b in bindings.values() if b['operation_kinds']==['process'] and
                    b['entry_boundary']=='in_process_backend' and b['config_sha256']==fill['fill_config_sha256'] and
                    fill['source_id'] in b['source_ids']]
                if len(fill_bindings)!=1:raise ValueError('one exact direct fill computation binding required')
                expected.add(fill_bindings[0]['binding_id'])
        if expected!=set(bindings):raise ValueError('unused or missing original runtime provider binding')


def _validate_numeric_inputs(d,u,latency_policy,bundles,inputs):
    from .matched_source_exposure import validate_recording_opportunities,validate_accounting_policy,validate_exposure_policy
    from .recording_financial import validate_adapters
    keys(inputs,('opportunities','exposure_policy','financial_adapter_inventory'))
    e=inputs['exposure_policy'];g=inputs['opportunities'];k=d.get('stream_protocol')
    if k is None:raise ValueError('Q2 requires original K2 accounting declaration')
    g=validate_recording_opportunities(g,expected_sha256=e['recordings_sha256'],comparison_plan_sha256=digest(d['plan']))
    k=validate_accounting_policy(k,expected_sha256=u['accounting_policy_sha256'],comparison_plan_sha256=digest(d['plan']),recordings=g)
    e=validate_exposure_policy(e,d['plan'],g,expected_sha256=u['numeric_policy_sha256'],expected_recordings_sha256=digest(g))
    validate_adapters(inputs['financial_adapter_inventory'],expected_sha256=e['financial_adapter_inventory_sha256'])
    if (e['latency_policy_sha256']!=digest(latency_policy) or e['accounting_policy_sha256']!=digest(k) or
            k['financial_adapter_inventory_sha256']!=e['financial_adapter_inventory_sha256'] or
            d['scope_protocol']['recording_reconciliation_sha256']!=digest(e)):
        raise ValueError('prospective numeric protocol identity mismatch')
    if e['limits']!=k['limits']:raise ValueError('E2/K2 cannot reset joint limits')
    c=d['collection'];groups=g['groups']
    if len(groups)!=len(c['recordings']):raise ValueError('all original matched recordings required')
    for original,group in zip(c['recordings'],groups):
        bundle=bundles[original['recording_id']];source=bundle['manifest']
        if (group['recording_id']!=original['recording_id'] or group['source_manifest_sha256']!=digest(source) or
                group['tasks_sha256']!=digest(bundle['tasks']) or group['exposure_duration_ns']!=source['duration_ns'] or
                group['availability_sha256']!=digest(source['availability'])):
            raise ValueError('matched opportunity differs from original recording')
        expected=[]
        for sensor in source['sources']:
            records=[r for r in source['records'] if r['source_id']==sensor['source_id']]
            expected.append(dict(source_id=sensor['source_id'],sensor_id=sensor['sensor_id'],
                original_stream_epoch=sensor['stream_epoch'],format=sensor['format'],calibration_id=sensor['calibration_id'],
                record_count=len(records),record_inventory_sha256=digest(records),counter_contract='attempted_equals_captured_plus_dropped'))
        if group['sources']!=expected:raise ValueError('matched original source inventory differs')
        order=[inv['arm'] for inv in c['invocations'] if inv['recording_index']==c['recordings'].index(original)]
        if group['arm_order']!=order:raise ValueError('matched original arm order differs')
    streams={(row['recording_id'],row['arm']):row for row in k['streams']}
    for inv in c['invocations']:
        rid=c['recordings'][inv['recording_index']]['recording_id']
        if streams[rid,inv['arm']]['stream_id']!=inv['stream_id']:raise ValueError('K2 original stream differs')


def preflight_runtime_collection(recording_declarations,*,latency_policy,source_bundles,numeric_inputs=None):
    from .recording_native_schema import sequence,_preflight_collection_common
    checked=[validate_runtime_scope_protocol(d,latency_policy=latency_policy,
        source_bundles=source_bundles,numeric_inputs=numeric_inputs)
        for d in sequence(recording_declarations,32,1)]
    return _preflight_collection_common(checked)


def validate_runtime_native_inventory(declarations,index,terminal=None,*,source_inventory,
                                      latency_policy,source_bundles,numeric_inputs=None):
    from .recording_native_validation import _validate_native_inventory_common
    d=validate_runtime_scope_protocol(declarations,latency_policy=latency_policy,
        source_bundles=source_bundles,numeric_inputs=numeric_inputs)
    return _validate_native_inventory_common(d,index,terminal,source_inventory=source_inventory)


def load_runtime_declarations(bootstrap,*,latency_policy,source_bundles,numeric_inputs=None):
    from .recording_native_channel import _load_declaration_documents
    from .recording_native_schema import run_context
    result=validate_runtime_scope_protocol(_load_declaration_documents(bootstrap),
        latency_policy=latency_policy,source_bundles=source_bundles,numeric_inputs=numeric_inputs)
    context=run_context(result,bootstrap['nonce'],bootstrap['invocation_ordinal'])
    for name in ('collection_sha256','scope_protocol_sha256','instrumentation_protocol_sha256'):
        if bootstrap[name]!=context[name]:raise ValueError('runtime bootstrap original identity mismatch')
    return result


from .recording_native_channel import ParentNativeChannel,ChildNativeChannel


class RuntimeParentNativeChannel(ParentNativeChannel):
    def __init__(self,context,declarations,*,latency_policy,source_bundles,numeric_inputs=None,
                 paths,output,deadline_ns,budget=None,retain_financial_documents=False,
                 collection_declarations=None):
        from .recording_native_schema import _freeze
        d=validate_runtime_scope_protocol(declarations,latency_policy=latency_policy,
            source_bundles=source_bundles,numeric_inputs=numeric_inputs)
        bundles=[d] if collection_declarations is None else collection_declarations
        preflight=preflight_runtime_collection(bundles,latency_policy=latency_policy,
            source_bundles=source_bundles,numeric_inputs=numeric_inputs)
        self._runtime_latency=_freeze(snapshot(latency_policy))
        self._runtime_sources=_freeze(snapshot(source_bundles))
        self._runtime_numeric=None if numeric_inputs is None else _freeze(snapshot(numeric_inputs))
        self._initialize(context,d,paths=paths,output=output,deadline_ns=deadline_ns,budget=budget,
            retain_financial_documents=retain_financial_documents,preflight=preflight,bundles=bundles)

    def _load_original_declarations(self):
        return load_runtime_declarations(self.bootstrap,latency_policy=snapshot(self._runtime_latency),
            source_bundles=snapshot(self._runtime_sources),numeric_inputs=None if self._runtime_numeric is None else snapshot(self._runtime_numeric))

    def _validate_original_inventory(self):
        return validate_runtime_native_inventory(self.declarations,self.output,
            source_inventory=self.declarations['source_manifest'],latency_policy=snapshot(self._runtime_latency),
            source_bundles=snapshot(self._runtime_sources),numeric_inputs=None if self._runtime_numeric is None else snapshot(self._runtime_numeric))


class RuntimeChildNativeChannel(ChildNativeChannel):
    @classmethod
    async def from_runtime_environment(cls,*,latency_policy,source_bundles,numeric_inputs=None):
        import asyncio,os,socket,time
        from .recording_native_channel import FD_ENVIRONMENT_KEY,validate_bootstrap,_deadline,receive,frame,_hello
        from .recording_artifacts import _finish
        value=os.environ.get(FD_ENVIRONMENT_KEY)
        if type(value) is not str or not value.isascii() or not value.isdecimal() or value!=str(int(value)) or int(value)<3:
            raise ValueError('explicit inherited native socket FD required')
        fd=int(value);os.set_inheritable(fd,False);sock=socket.socket(fileno=fd);sock.setblocking(False)
        try:
            bootstrap=validate_bootstrap(await _deadline(receive(sock),time.monotonic_ns()+10_000_000_000))
            task=asyncio.create_task(asyncio.to_thread(load_runtime_declarations,bootstrap,
                latency_policy=latency_policy,source_bundles=source_bundles,numeric_inputs=numeric_inputs))
            try:declarations=await asyncio.shield(task)
            except asyncio.CancelledError:await _finish(task);raise
            limit=min(bootstrap['deadline_ns'],time.monotonic_ns()+declarations['instrumentation_protocol']['hello_timeout_ms']*1000000)
            await _deadline(asyncio.get_running_loop().sock_sendall(sock,frame(_hello(bootstrap))),limit)
            return cls(sock,bootstrap,declarations)
        except BaseException:sock.close();raise
