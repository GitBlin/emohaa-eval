import json
from pathlib import Path
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import time
import unittest
from evaluate_efficiency import measure, summary, text_gap_metrics
from emobench_api import Client

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        def event(obj):
            self.wfile.write(('data:'+json.dumps(obj)+'\n\n').encode());self.wfile.flush()
        event({'type':'meta.info','choices':[{'delta':{'content':'metadata'}}]})
        event({'choices':[{'delta':{'content':'','reasoning_content':'thinking'}}]})
        time.sleep(.15)
        if data.get('error'):
            event({'model':'error','choices':[{'delta':{'content':'bad'}}]});return
        # Deliberately split the event across writes.
        self.wfile.write(b'data:{"choices":[{"delta":');self.wfile.flush();time.sleep(.05)
        self.wfile.write(b'{"content":"OK"}}]}\n\n');self.wfile.flush()
        time.sleep(.1)
        if data.get('disconnect'):return
        event({'choices':[{'finishReason':'stop'}]})

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def run_case(self,payload):
        with tempfile.TemporaryDirectory() as d:
            c=Client(f'http://127.0.0.1:{self.server.server_port}','x','x','test');c.token='test'
            try:return measure(c,payload,Path(d))
            finally:c.session.close()
    def test_event_gaps_ignore_metadata_and_separate_tail(self):
        def e(t,content,typ=''):
            return {'elapsed_seconds':t,'data':{'type':typ,'choices':[{'delta':{'content':content}}]}}
        events=[e(.1,'meta','meta.info'),e(1,'Hello'),e(2,'thinking','reasoning'),e(3,' '),e(4,'world')]
        m=text_gap_metrics(events,5)
        self.assertEqual(m['text_gap_seconds'],[3]);self.assertEqual(m['tail_wait_seconds'],1)
        self.assertEqual(m['text_event_count'],2)
        self.assertIsNone(text_gap_metrics([e(1,'one')],2)['max_text_gap_seconds'])
        self.assertIsNone(text_gap_metrics(events)['tail_wait_seconds'])
    def test_timing_and_exclusions(self):
        r=self.run_case({});self.assertTrue(r['success']);self.assertEqual(r['reply'],'OK')
        self.assertIsNone(r['max_text_gap_seconds'])
        self.assertGreaterEqual(r['tail_wait_seconds'],.08)
        self.assertGreaterEqual(r['first_text_seconds'],.18)
        self.assertLess(r['first_text_seconds'],r['complete_seconds']-.06)
    def test_error_not_first_text(self):
        r=self.run_case({'error':True});self.assertFalse(r['success']);self.assertIsNone(r['first_text_seconds'])
    def test_partial_failure_denominator(self):
        r=self.run_case({'disconnect':True});self.assertFalse(r['success']);self.assertIsNotNone(r['first_text_seconds']);self.assertIsNone(r['complete_seconds'])
        s=summary([r]);self.assertEqual(s['success_rate'],0);self.assertEqual(s['first_text']['n'],1);self.assertEqual(s['successful_and_first_text_within']['3'],0)

if __name__=='__main__':unittest.main()
