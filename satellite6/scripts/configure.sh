satellite-installer --scenario satellite \
--verbose \
--foreman-initial-organization "redhat" \
--foreman-initial-location "lab" \
--foreman-admin-username admin \
--foreman-admin-password redhat


satellite-installer --scenario satellite \
--verbose \
--enable-foreman-plugin-remote-execution \
--enable-foreman-proxy-plugin-remote-execution-ssh \
--enable-foreman-plugin-bootdisk \
--enable-foreman-plugin-discovery \
--foreman-websockets-encrypt=false \
--foreman-proxy-tftp=true \
--foreman-proxy-bmc=true \
--foreman-proxy-puppetrun=true \
--foreman-proxy-plugin-remote-execution-ssh-enabled=true \
--foreman-proxy-plugin-remote-execution-ssh-generate-keys=false \
--foreman-plugin-discovery-install-images=true


satellite-installer --scenario satellite \
--verbose \
--foreman-proxy-dhcp=true \
--foreman-proxy-dhcp-gateway="192.168.4.250" \
--foreman-proxy-dhcp-range="192.168.4.100 192.168.4.200" \
--foreman-proxy-dhcp-nameservers="192.168.4.2,192.168.3.2" \
--foreman-proxy-dhcp-option-domain="example.com"


satellite-installer --scenario satellite \
--verbose \
--foreman-proxy-dns=true \
--foreman-proxy-dns-provider=nsupdate_gss \
--foreman-proxy-dns-reverse="4.168.192.in-addr.arpa" \
--foreman-proxy-dns-server=192.168.3.2 \
--foreman-proxy-dns-zone=example.com \
--foreman-proxy-dns-tsig-principal="foremanproxy/satellite6.example.com@EXAMPLE.COM" \
--foreman-proxy-dns-tsig-keytab="/etc/foreman-proxy/dns.keytab"


satellite-installer --scenario satellite \
--verbose \
--foreman-proxy-realm=true \
--foreman-proxy-realm-keytab="/etc/foreman-proxy/freeipa.keytab" \
--foreman-proxy-realm-principal="realm-proxy@EXAMPLE.COM"
