import os
import testinfra.utils.ansible_runner


testinfra_ansible_runner = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE'])
testinfra_hosts = testinfra_ansible_runner.get_hosts('ansible-test-ns2')

ns1_facts = testinfra_ansible_runner.run_module('ansible-test-ns1', 'setup', None)['ansible_facts']


def test_recursive_ok_ip4(host):
    r = host.check_output("dig -4 www.redhat.com. @%s" % ns1_facts['ansible_default_ipv4']['address'])
    assert "WARNING: recursion requested but not available" not in r

def test_recursive_ok_ip6(host):
    r = host.check_output("dig -6 www.redhat.com. @%s" % ns1_facts['ansible_default_ipv6']['address'])
    assert "WARNING: recursion requested but not available" not in r

