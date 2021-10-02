# Ansible role for Bind 9 installation

## Introduction

[Bind9](https://bind9.net/) is a DNS server.

This role installs and configure the application. Installation of zone files needs to be done in your playbook.

Currently this role can handle these functions:
  - caching server
  - NS1
  - NS2

Communication between NS1 and NS2 can be secured using TSIG.


Configuration example:

    - hosts: 127.0.0.1
      roles:
      - role: bind9
        dnssec_system: opendnssec
        keys:
          # you can create it using: /usr/sbin/dnssec-keygen -a HMAC-SHA512 -b 512 -n HOST taiste
          # and taking the 'Key' part in 'Ktaiste.*.private' file, to put into the 'secret' field below
          datacenter_key1:
            algorithm: hmac-sha512
            secret: "LjupS1RkUB3qrMmyEOPpvb7ocPe+x76c/cowiYB3FHXqYJzM6cSFup2T323ysYIbHCb5Ft2ooWfRuLEfR8PnEg=="
          datacenter_key2:
            algorithm: hmac-sha512
            secret: "cnnKyLXlEYPctrqRd+1boZzrq5htBdiB63kYPRnxU+M4iVw4GRS/jL/Q ZdcVR9JTVGd+77+97cZsnGpKYemOMw=="
        server_groups:
          datacenter_ns1:
            ips:
              - 192.168.2.1
              - 2001:123:456::1
            key: datacenter_key1
          datacenter_ns2:
            ips:
              - 192.168.2.30
              - 2001:123:456::30
            key: datacenter_key2
          bastion:
            ips:
              - 192.168.2.254
          neighbors:
            ips:
              - 192.168.1.0/24
        master_zones:
          toto.net:
            transfer_groups:
              - datacenter_ns2
              - bastion
          secure.net:
            transfer_groups:
              - datacenter_ns2
            dnssec: True
            #dnssec_policy: custom
        slave_zones:
          pouet.org:
            master_groups:
              - datacenter_ns1
        recursion_allowed_groups:
          - neighbors
        options:
          # turns off IPv6
          listen-on-v6: "{ none; }"

Master zones are to be installed in the `masters` subdirectory of the configuration path.
Signed master zones (if using DNSSEC) shoule be generated in ``masters/signed`. Such
generation is not done in this role.


## Variables

- **dnssec_system**: choose between `opendnssec` (the default) and `bind` (using inline-signing)
- **keys**: list of keys used to setup TSIG security when transfering zones between servers
            each key has a name and is defined by an 'algorithm' and a 'secret', see configuration example
- **server_groups**: list of server(s), defined by their 'ips'
                     if an ip contains a percent, then <ip>%<port> is assumed
                     optionally, if a 'key' is given, setup TSIG security when conversing with these IPs
- **master_zones**: list of master zones
                    remote hosts allowed to modify the zone are defined in 'update_groups'
                    alternatively you may use 'update_policy' (raw grant/deny lines)
                    if both are specified, 'update_groups' is ignored
                    transfer servers are defined using groups defined in 'server_groups'
                    masters to also notify are optionally defined in 'notify_groups'
                    if `dnssec` is True, then DNSSEC support will be enabled for the zone (what is done
                    depends on the value of `dnssec_system`, see the DNSSEC chapter)
- **slave_zones**: list of slave zones
                   master servers are defined using groups defined in 'server_groups'
- **recursion_allowed_groups:**: list of machines allowed to ask for recursion
                                 these machines are defined using groups defined in 'server_groups'
- **options**: list of global options. Very few basic settings (`directory`, `pid-file`, `session-keyfile`,
               `managed-keys-directory`) can't be changed this way as they are specific to the packaging.
               `allow-recursion` is managed using the `recursion_allowed_groups` setting instead.
               Other settings may have an overridable default.
               If the value needs quoting, be sure to add it into the value.
- **dnssec_params**: if DNSSEC using Bind is in use (`dnssec_system` == `bind`), then you can change the
                     default key management policy in this dictionnary (see `vars/dnssec_1.yml`)
                     This is only used with Bind <9.16.
- **dnssec_policy**: if DNSSEC using Bind is in use (`dnssec_system` == `bind`), then you can change the
                     default key management policy in this dictionnary (see `vars/dnssec_2.yml`)
                     This is only used with Bind >=9.16.

## DNSSEC

### OpenDNSSEC

If `dnssec_system` == `opendnsec` then Bind will be configured to load the zone from the `signed/` subdirectory for zones having the `dnssec` flag set to True.
This made in order to work with the `opendnssec` role which will configure OpenDNSSEC to take the original zone and output a signed zone in this very place.

### Bind

Depending on the version of Bind the method changed slightly.

#### Bind >= 9.11 and < 9.16 (dnssec-keymgr method)

Inline-signing and key management is enabled for zones having the `dnssec` flag set to True.

New zones will have their keys created according to the policy. NSEC3 will also be activated.

Everyday all zones will be checked for key rollover and creation of new keys, according to the policy. NSEC3 is enabled when keys are first created for a zone.

Publishing of the key(s) in the parent zone may not be handled automatically. dnssec-keymgr is not able to setup CDS/CDNSKEY (RFC 7344), and your registry would also need to support it.

#### Bind >= 9.16 (dnssec-policy method)

The KASP is enabled for zones having the `dnssec` flag set to True.

Bind will by itself create needed keys, and care about the ZSK rollover and provide a KSK rollover trigger. The role's generated policy is used by default but you can include a custom configuration and use `dnssec_policy` in the zone parameters to use a custom policy if needed. If `dnssec_policy` is set to `insecure`, then the zone will be converted to a non-DNSSEC zone and you will be able to remove the dnssec configuration after a safe delay.

Unfortunately Bind before 9.16.10 is not able to apply a NSEC3 policy, so the role can check your zones and enable it for you if you use the `postinst` entrypoint (with the same parameters).

CDS/CDNSKEY (RFC 7344) RRs are automatically generated but you still need to handle the publishing in the parent zone. If you do not control the parent zone, then the provider may support CDS/CDNSKEY, provide an API, or will need to update it manually (provider/s web UI…). If you manage a parent zone and wish to update delegation records automatically, then check the next chapter.

## DNSSEC Delegation Trust Maintenance (RFC 7344)

This feature only works with Bind >= 9.16.

If you managed a DNSSEC-signed domain which has DNSSEC-signed sub-domains, you can automatically update delegations securely if they publish CDS/CDNSKEY RRs; you don't need to have control over the servers publishing the sub-domains.

If you declare the list of sub-domains components (the top level component of the sub-domain) in `dnssec_children` in the zone parameters then the feature will be enabled for the zone. A script will be called regularly to check if new CDS/CDNSKEY RRs are published in the child zone, do some security check (done by `dnssec-cds`), and update the delegation in the parent zone.

For this feature to work there are several requirements:
  - the zone must not be dynamic (not supported yet)
  - the serial needs to be on a single line with the "serial" word as comment (to safely be able to increase it) (spaces and case do not matter)
  - the `/var/cache/bind/masters/<domain>.dnssec_children` file must be included in the parent zone (contain the generated delegations for all sub-domains)

If the parent zone already contained delegations, then it can be replaced by the INCLUDE once first generated.

If the parent zone had no delegations for certain sub-domains, then the CDS/CDNSKEY RRs published by the sub-domains' zones will be initially trusted.

Zone example:

    $ORIGIN secure.net.
    $TTL 3600
    @	SOA	ns1.secure.net.	hostmaster.secure.net. (
    		123        ; serial
    		3600       ; refresh
    		3600       ; retry
    		604800     ; expire
    		3600       ; minimum TTL
                )
    $INCLUDE /var/cache/bind/masters/secure.net.dnssec_children
    …

Configuration example:

    - hosts: 127.0.0.1
      roles:
      - role: bind9
        dnssec_system: bind
        keys:
          …
        server_groups:
          …
        master_zones:
          secure.net:
            transfer_groups:
              - datacenter_ns2
            dnssec: True
            #dnssec_policy: custom
            dnssec_children:
              # for sub1.secure.net
              - sub1
              # for sub2.secure.net
              - sub2

## Firewalling configuration

By default the role opens the needed ports using Firewalld. You can disable this by setting `manage_firewall` to False.

## Post Installation

After the role deployed Bind, you can install the zones' files and use the "reload DNS system" hook to ensure zones are reloaded. Then you need to make sure the service is started. Since you need the directories to be created to install the zones and the service cannot work without them installed either, it needs to happen in between.

The `postinst` entrypoint makes sure the service is started. It is also useful in a certain situation when using DNSSEC. Thus it is recommanded to use it after installing your zones' files.

