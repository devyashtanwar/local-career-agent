import math
import unittest
from types import SimpleNamespace
from operations.pc_status import GPU_COMMAND, SERVICE_COMMAND, collect, memory_from_text, parse_gpus

MEM='MemTotal: 16777216 kB'+chr(10)+'MemAvailable: 8388608 kB'+chr(10)

class PcStatusTests(unittest.TestCase):
    def test_memory_uses_available_not_free(self):
        self.assertEqual(memory_from_text(MEM),{'total_gib':16.0,'available_gib':8.0,'used_gib':8.0})
    def test_invalid_memory_refused(self):
        for text in ['', 'MemTotal: nan kB', MEM.replace('8388608','33554432')]:
            with self.subTest(text=text),self.assertRaises(ValueError): memory_from_text(text)
    def test_gpu_csv(self):
        row=parse_gpus('NVIDIA GeForce RTX 3060, 1024, 12288, 4, 51')[0]
        self.assertEqual(row['memory_used_mib'],1024.0)
        self.assertEqual(row['utilization_percent'],4.0)
    def test_unsupported_gpu_metrics_are_unknown(self):
        row=parse_gpus('GPU, 0, 12288, [N/A], N/A')[0]
        self.assertIsNone(row['utilization_percent']);self.assertIsNone(row['temperature_c'])
    def test_invalid_gpu_values_refused(self):
        for text in ['GPU, nan, 12288, 0, 50','GPU, 20000, 12288, 0, 50','GPU, 0, 12288, 101, 50','broken']:
            with self.subTest(text=text),self.assertRaises(ValueError): parse_gpus(text)
    def fake_read(self,path): return MEM if str(path).endswith('meminfo') else '3600.0 0.0'
    def fake_run(self,command):
        if command==GPU_COMMAND:return SimpleNamespace(returncode=0,stdout='GPU, 1024, 12288, 4, 51')
        self.assertEqual(command,SERVICE_COMMAND)
        return SimpleNamespace(returncode=3,stdout='active'+chr(10)+'active'+chr(10)+'inactive'+chr(10)+'active'+chr(10))
    def test_complete_collection_uses_only_fixed_commands(self):
        report=collect(run=self.fake_run,read=self.fake_read,disk=lambda p:SimpleNamespace(total=100*1024**3,free=40*1024**3,used=60*1024**3),load=lambda:(0.5,0,0))
        self.assertEqual(report['uptime_seconds'],3600.0)
        self.assertEqual(report['services']['career-local-model.service'],'inactive')
        self.assertFalse(report['action_authorized']);self.assertTrue(report['gpu']['available'])
    def test_missing_commands_do_not_crash_other_collectors(self):
        def missing(command):raise FileNotFoundError()
        report=collect(run=missing,read=self.fake_read)
        self.assertFalse(report['gpu']['available'])
        self.assertTrue(all(value=='unavailable' for value in report['services'].values()))
        self.assertEqual(report['memory']['total_gib'],16.0)
    def test_timeout_is_reported_without_inventing_values(self):
        import subprocess
        def timed_out(command):raise subprocess.TimeoutExpired(command,3)
        report=collect(run=timed_out,read=self.fake_read)
        self.assertEqual(report['gpu']['error'],'timeout');self.assertEqual(report['gpu']['devices'],[])
    def test_failed_gpu_and_malformed_service_output(self):
        def failed(command):return SimpleNamespace(returncode=1,stdout='unexpected output')
        report=collect(run=failed,read=self.fake_read)
        self.assertFalse(report['gpu']['available'])
        self.assertTrue(all(value=='unavailable' for value in report['services'].values()))

if __name__=='__main__':unittest.main()
