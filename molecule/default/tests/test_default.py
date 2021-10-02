import os
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('ns_servers')


def test_service(host):
    srv = host.service("named")
    assert srv.is_running
    assert srv.is_enabled

def test_socket(host):
    host.socket("tcp://53").is_listening

def test_resolution_ip4(host):
    host.run_expect([0], "dig -4 test.example.org. @127.0.0.1")

def test_resolution_ip6(host):
    host.run_expect([0], "dig -6 test.example.org. @::1")

