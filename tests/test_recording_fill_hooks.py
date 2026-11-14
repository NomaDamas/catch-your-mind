"""Actual OpenCV case keeps opt-in export outside rule/stage selection."""
import threading
import unittest
from humansense.fill_evaluation import FillEvaluationContext
import test_fill_conflict as fill_tests


class Context(FillEvaluationContext):
    def __init__(self):self.rows=[];self.measure_thread=None;self.finished=[];self.outcome=None
    def validate(self,driver,frame):self.driver=driver
    def measure(self,callback):self.measure_thread=threading.get_ident();return callback()
    def published(self,role,record):self.rows.append((role,record))
    def stage_arguments(self,stage,request_id,adapter):
        return dict(evaluation_scope=None,evaluation_relationship='root',evaluation_predecessor=None)
    def stage_finished(self,stage,request_id,response,error):self.finished.append((stage,response,error))
    def completed(self,case,record):self.case=case
    def closed(self,outcome):self.outcome=outcome


@unittest.skipIf(fill_tests.np is None,'existing vision dependencies required')
class FillHooks(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fill_tests.Runtime.asyncSetUp
    asyncTearDown=fill_tests.Runtime.asyncTearDown
    create=fill_tests.Runtime.create

    async def test_actual_measurement_and_accepted_records_export_with_original_capture(self):
        driver,controller,requests=self.create([[.48,.52]])
        context=Context();frame=fill_tests.frame()
        result=await driver.inspect(frame,evaluation_context=context)
        self.assertNotEqual(context.measure_thread,threading.get_ident())
        self.assertEqual([role for role,record in context.rows],['fill_measurement','fill_descriptor','fill_comparison'])
        self.assertTrue(all(record['timestamp_ms']==frame.timestamp_ms for role,record in context.rows))
        self.assertEqual(context.rows[-1][1],result)
        self.assertEqual(context.case['outcome'],'consistent_under_rule')
        self.assertEqual(context.outcome,'completed');self.assertEqual(context.finished[0][0],'initial')
        self.assertEqual(len(requests),1)

    async def test_unrecorded_retry_relationship_is_rejected_without_extra_callback(self):
        driver,controller,requests=self.create([[.1,.2]])
        context=Context()
        with self.assertRaisesRegex(ValueError,'relationship differs'):
            await driver.inspect(fill_tests.frame(),evaluation_context=context)
        self.assertEqual(len(requests),1);self.assertEqual(context.outcome,'failed')
