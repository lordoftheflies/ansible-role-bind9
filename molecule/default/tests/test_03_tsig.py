import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('ansible-test-ns1')


def test_tsig(host):
    host.run_expect([0], "journalctl -u named | grep \"transfer of 'example.org/IN': AXFR started: TSIG testkey\"")

