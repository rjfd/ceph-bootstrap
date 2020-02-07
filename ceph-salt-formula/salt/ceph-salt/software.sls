{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Install and update required packages') }}

install required packages:
  pkg.installed:
    - pkgs:
      - iputils
      - lsof
      - podman
    - failhard: True

{% if pillar['ceph-salt'].get('upgrades', {'enabled': True})['enabled'] %}

{{ macros.begin_step('Upgrading all packages') }}

upgrade packages:
  module.run:
    - name: pkg.upgrade
    - failhard: True

{{ macros.end_step('Upgrading all packages') }}

{% else %}

upgrades disabled:
  test.nop

{% endif %}

{{ macros.end_stage('Install and update required packages') }}

{% if pillar['ceph-salt'].get('upgrades', {'reboot': True})['reboot'] %}

reboot:
   ceph_salt.reboot_if_needed:
     - failhard: True

{% endif %}
