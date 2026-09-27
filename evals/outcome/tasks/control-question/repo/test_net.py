import io
import unittest
import urllib.error

import net


def fake_opener(outcomes):
    calls = iter(outcomes)

    def opener(url, timeout):
        o = next(calls)
        if isinstance(o, Exception):
            raise o
        return io.BytesIO(o)
    return opener


def http_error(code, headers=None):
    return urllib.error.HTTPError("http://x", code, "err", headers or {}, None)


class FetchTest(unittest.TestCase):
    def test_retries_then_succeeds(self):
        waits = []
        body = net.fetch("http://x", opener=fake_opener([http_error(503), b"ok"]), sleep=waits.append)
        self.assertEqual(body, b"ok")
        self.assertEqual(len(waits), 1)

    def test_404_not_retried(self):
        with self.assertRaises(urllib.error.HTTPError):
            net.fetch("http://x", opener=fake_opener([http_error(404)]), sleep=lambda s: None)

    def test_gives_up(self):
        with self.assertRaises(net.FetchError):
            net.fetch("http://x", attempts=3, opener=fake_opener([http_error(502)] * 3), sleep=lambda s: None)


if __name__ == "__main__":
    unittest.main()
