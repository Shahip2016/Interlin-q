from components.controller_host import ControllerHost
from objects.circuit import Circuit
from objects.layer import Layer
from objects.operation import Operation

from qunetsim.components.network import Network
from qunetsim.backends import EQSNBackend

import unittest


class TestControllerHost(unittest.TestCase):

    # Runs before all tests
    @classmethod
    def setUpClass(cls) -> None:
        pass

    # Runs after all tests
    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self):
        network = Network.get_instance()
        network.start(["host_1"], EQSNBackend())

        self.controller_host = ControllerHost(
            host_id="host_1",
            computing_host_ids=["QPU_1"])
        network.add_host(self.controller_host)

        self._network = network

    def tearDown(self):
        self._network.stop(True)

    def test_instantiation(self):
        self.assertEqual(self.controller_host.host_id, "host_1")
        self.assertEqual(self.controller_host.computing_host_ids, ["QPU_1"])
        self.assertEqual(self.controller_host._get_operation_execution_time("QPU_1", "SINGLE", "X"), 1)

        self.controller_host.connect_host("QPU_2")
        self.assertEqual(self.controller_host.computing_host_ids, ["QPU_1", "QPU_2"])
        self.assertEqual(self.controller_host._get_operation_execution_time("QPU_1", "REC_ENT", None), 1)

    def test_distributed_scheduler(self):
        self.controller_host.connect_host("QPU_2")

        q_map = {
            'qubit_1': 'QPU_1',
            'qubut_2': 'QPU_1',
            'qubit_3': 'QPU_2',
            'qubit_4': 'QPU_2'}

        # Form layer 1
        op_1 = Operation(
            name="SINGLE",
            qids=["qubit_1"],
            gate="H",
            computing_host_ids=["QPU_1"])

        op_2 = Operation(
            name="SEND_ENT",
            qids=["qubit_2", "qubit_3"],
            computing_host_ids=["QPU_1", "QPU_2"])

        op_3 = Operation(
            name="REC_ENT",
            qids=["qubit_3", "qubit_2"],
            computing_host_ids=["QPU_2", "QPU_1"])

        layer_1 = Layer([op_1, op_2, op_3])

        # Form layer 2
        op_1 = Operation(
            name="TWO_QUBIT",
            qids=["qubit_3", "qubit_4"],
            gate="cnot",
            computing_host_ids=["QPU_2"])

        layer_2 = Layer([op_1])

        # Form layer 3
        op_1 = Operation(
            name="MEASURE",
            qids=["qubit_3"],
            cids=["bit_1"],
            computing_host_ids=["QPU_2"])

        layer_3 = Layer([op_1])

        # Form layer 4
        op_1 = Operation(
            name="SEND_CLASSICAL",
            cids=["bit_1"],
            computing_host_ids=["QPU_2", "QPU_1"])

        op_2 = Operation(
            name="REC_CLASSICAL",
            cids=["bit_1"],
            computing_host_ids=["QPU_1", "QPU_2"])

        layer_4 = Layer([op_1, op_2])

        # Form layer 5
        op_1 = Operation(
            name="CLASSICAL_CTRL_GATE",
            qids=["qubit_1"],
            cids=["bit_1"],
            gate="X",
            computing_host_ids=["QPU_1"])

        layer_5 = Layer([op_1])

        layers = [layer_1, layer_2, layer_3, layer_4, layer_5]
        circuit = Circuit(q_map, layers)

        computing_host_schedules = self.controller_host._create_distributed_schedule(circuit)

        self.assertEqual(len(computing_host_schedules), 2)
        self.assertEqual(len(computing_host_schedules['QPU_1']), 4)
        self.assertEqual(len(computing_host_schedules['QPU_2']), 4)

        self.assertEqual(computing_host_schedules['QPU_1'][0]['name'], "SINGLE")
        self.assertEqual(computing_host_schedules['QPU_1'][0]['layer_end'], 0)
        self.assertEqual(computing_host_schedules['QPU_1'][1]['name'], "SEND_ENT")
        self.assertEqual(computing_host_schedules['QPU_1'][1]['layer_end'], 0)
        self.assertEqual(computing_host_schedules['QPU_1'][2]['name'], "REC_CLASSICAL")
        self.assertEqual(computing_host_schedules['QPU_1'][2]['layer_end'], 3)
        self.assertEqual(computing_host_schedules['QPU_1'][3]['name'], "CLASSICAL_CTRL_GATE")
        self.assertEqual(computing_host_schedules['QPU_1'][3]['layer_end'], 4)

        self.assertEqual(computing_host_schedules['QPU_2'][0]['name'], "REC_ENT")
        self.assertEqual(computing_host_schedules['QPU_2'][0]['layer_end'], 0)
        self.assertEqual(computing_host_schedules['QPU_2'][1]['name'], "TWO_QUBIT")
        self.assertEqual(computing_host_schedules['QPU_2'][1]['layer_end'], 1)
        self.assertEqual(computing_host_schedules['QPU_2'][2]['name'], "MEASURE")
        self.assertEqual(computing_host_schedules['QPU_2'][2]['layer_end'], 2)
        self.assertEqual(computing_host_schedules['QPU_2'][3]['name'], "SEND_CLASSICAL")
        self.assertEqual(computing_host_schedules['QPU_2'][3]['layer_end'], 3)