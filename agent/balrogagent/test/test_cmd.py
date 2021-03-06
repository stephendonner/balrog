import aiohttp
import asyncio
import asynctest
import json

from ..cmd import run_agent


@asynctest.patch("balrogagent.client.request")
@asynctest.patch("balrogagent.cmd.telemetry_is_ready")
@asynctest.patch("balrogagent.cmd.time_is_ready")
class TestRunAgent(asynctest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()

    async def _runAgent(self, scheduled_changes, request):
        def side_effect(balrog_api_root, endpoint, auth, loop, method='GET'):
            endpoint = endpoint.split('/')[-1]
            response = aiohttp.client.ClientResponse("GET",
                                                     "http://balrog.fake/scheduled_changes/%s" % endpoint)
            response.headers = {"Content-Type": "application/json"}
            changes = scheduled_changes.get(endpoint) or []
            if method != 'GET':
                body = ""
            else:
                body = {"count": len(changes), "scheduled_changes": changes}
            response._content = bytes(json.dumps(body), "utf-8")
            return response

        request.side_effect = side_effect

        return await run_agent(self.loop, "http://balrog.fake", "balrog", "balrog", "telemetry", once=True, raise_exceptions=True)

    async def testNoChanges(self, time_is_ready, telemetry_is_ready, request):
        sc = {}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 0)
        self.assertEquals(request.call_count, 3)

    @asynctest.patch("time.time")
    async def testTimeBasedNotReadyRules(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 0
        time_is_ready.return_value = False
        sc = {'rules': [{"sc_id": 4, "when": 23456789, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 1)
        self.assertEquals(request.call_count, 3)

    @asynctest.patch("time.time")
    async def testTimeBasedNotReadyReleases(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 0
        time_is_ready.return_value = False
        sc = {'releases': [{"sc_id": 4, "when": 23456789, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 1)
        self.assertEquals(request.call_count, 3)

    @asynctest.patch("time.time")
    async def testTimeBasedNotReadyPermissions(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 0
        time_is_ready.return_value = False
        sc = {'permissions': [{"sc_id": 4, "when": 23456789, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 1)
        self.assertEquals(request.call_count, 3)

    @asynctest.patch("time.time")
    async def testTimeBasedIsReadyRules(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 999999999
        time_is_ready.return_value = True
        sc = {'rules': [{"sc_id": 4, "when": 234, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 1)
        self.assertEquals(request.call_count, 4)

    @asynctest.patch("time.time")
    async def testTimeBasedIsReadyReleases(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 999999999
        time_is_ready.return_value = True
        sc = {'releases': [{"sc_id": 4, "when": 234, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 1)
        self.assertEquals(request.call_count, 4)

    @asynctest.patch("time.time")
    async def testTimeBasedIsReadyPermissions(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 999999999
        time_is_ready.return_value = True
        sc = {'permissions': [{"sc_id": 4, "when": 234, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 1)
        self.assertEquals(request.call_count, 4)

    @asynctest.patch("balrogagent.cmd.get_telemetry_uptake")
    async def testTelemetryBasedNotReady(self, get_telemetry_uptake, time_is_ready, telemetry_is_ready, request):
        telemetry_is_ready.return_value = False
        get_telemetry_uptake.return_value = 0
        sc = {'rules': [{"sc_id": 4, "when": None, "telemetry_uptake": 1000, "telemetry_product": "foo", "telemetry_channel": "bar"}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 1)
        self.assertEquals(time_is_ready.call_count, 0)
        self.assertEquals(request.call_count, 3)

    @asynctest.patch("balrogagent.cmd.get_telemetry_uptake")
    async def testTelemetryBasedIsReady(self, get_telemetry_uptake, time_is_ready, telemetry_is_ready, request):
        telemetry_is_ready.return_value = True
        get_telemetry_uptake.return_value = 20000
        sc = {'rules': [{"sc_id": 4, "when": None, "telemetry_uptake": 1000, "telemetry_product": "foo", "telemetry_channel": "bar"}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 1)
        self.assertEquals(time_is_ready.call_count, 0)
        self.assertEquals(request.call_count, 4)

    @asynctest.patch("time.time")
    async def testMultipleEndpointsAtOnce(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 999999999
        time_is_ready.return_value = True
        sc = {'releases': [{"sc_id": 4, "when": 234, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}],
              'rules': [{"sc_id": 5, "when": 234, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}],
              'permissions': [{"sc_id": 6, "when": 234, "telemetry_uptake": None, "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 3)
        self.assertEquals(request.call_count, 6)

    @asynctest.patch("time.time")
    async def testMultipleChangesOneEndpoint(self, time, time_is_ready, telemetry_is_ready, request):
        time.return_value = 999999999
        time_is_ready.return_value = True
        sc = {'releases': [{"sc_id": 4, "when": 234, "telemetry_uptake": None,
                            "telemetry_product": None, "telemetry_channel": None},
                           {"sc_id": 5, "when": 234, "telemetry_uptake": None,
                            "telemetry_product": None, "telemetry_channel": None},
                           {"sc_id": 6, "when": 234, "telemetry_uptake": None,
                            "telemetry_product": None, "telemetry_channel": None}]}
        await self._runAgent(sc, request)
        self.assertEquals(telemetry_is_ready.call_count, 0)
        self.assertEquals(time_is_ready.call_count, 3)
        self.assertEquals(request.call_count, 6)
        called_endpoints = [call[0][1] for call in request.call_args_list]
        self.assertIn('/scheduled_changes/releases', called_endpoints)
        self.assertIn('/scheduled_changes/permissions', called_endpoints)
        self.assertIn('/scheduled_changes/rules', called_endpoints)
        self.assertIn('/scheduled_changes/releases/4/enact', called_endpoints)
        self.assertIn('/scheduled_changes/releases/5/enact', called_endpoints)
        self.assertIn('/scheduled_changes/releases/6/enact', called_endpoints)
