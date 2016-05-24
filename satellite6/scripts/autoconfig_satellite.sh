#!/bin/bash

### Define Variables
export ORG=redhat
export LOC=lab
export SATUSER=admin
export SATPASS=redhat
export SATHOST=$(hostname -f)
export STAGEDIR="/root/satstage"
export MANIFEST="/root/satstage/manifest.zip"
export COUNTRIES="de uk fr"
export GITREPO="git@gitlab.example.com:ops/satscripts.git"
export RHEL5=0
export RHEL6=0
export RHEL7=1

######################################################## Functions
function get_cv {
	CVID=$(hammer --csv content-view list --name $1 --organization ${ORG} | grep -vi '^Content View ID,' | awk -F',' '{print $1}' )
	VID=$(hammer content-view version list --content-view-id ${CVID} | awk -F'|' '{print $1}' | sort -n | tac | head -n 1)
	echo $VID
	return 0
}

######################################################## make staging directory for manifest, puppet modules and rpms
mkdir -p ${STAGEDIR}

######################################################## clone git repo with manifest and puppet modules
echo "Cloning git repo..."
yum -y -q install git
rm -rf /root/satstage
git clone ${GITREPO} ${STAGEDIR}



# Create /root/.hammer/cli_config.yml
echo "Create hammer config..."
mkdir -p /root/.hammer
echo ":foreman:" > /root/.hammer/cli_config.yml
echo " :enable_module: true" >> /root/.hammer/cli_config.yml
echo " :host: 'https://localhost/'" >> /root/.hammer/cli_config.yml
echo " :username: ${SATUSER}" >> /root/.hammer/cli_config.yml
echo " :password: ${SATPASS}" >> /root/.hammer/cli_config.yml
echo " :request_timeout: -1" >> /root/.hammer/cli_config.yml

######################################################## Organisation stuff
echo "Creating organisation..."
hammer organization create --name=${ORG}

######################################################## Download and upload manifest
echo "Adding manifest..."
hammer subscription upload --file=${MANIFEST} --organization-label=${ORG}

######################################################## Enable Red hat Repositories
echo "Enabling Red Hat Repositories ..."
((RHEL7)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64' --releasever='7.2' \
--name 'Red Hat Enterprise Linux 7 Server (Kickstart)'

((RHEL7)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64' --releasever='7Server' \
--name 'Red Hat Enterprise Linux 7 Server (RPMs)'

((RHEL7)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64'  \
--name 'Red Hat Satellite Tools 6.1 (for RHEL 7 Server) (RPMs)'

((RHEL6)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64' --releasever='6.7' \
--name 'Red Hat Enterprise Linux 6 Server (Kickstart)'

((RHEL6)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64' --releasever='6Server' \
--name 'Red Hat Enterprise Linux 6 Server (RPMs)'

((RHEL6)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64'  \
--name 'Red Hat Satellite Tools 6.1 (for RHEL 6 Server) (RPMs)'

((RHEL5)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64' --releasever='5.11' \
--name 'Red Hat Enterprise Linux 5 Server (Kickstart)'

((RHEL5)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64' --releasever='5Server' \
--name 'Red Hat Enterprise Linux 5 Server (RPMs)'

((RHEL5)) && hammer repository-set enable --organization "$ORG" \
--product 'Red Hat Enterprise Linux Server' \
--basearch='x86_64'  \
--name 'Red Hat Satellite Tools 6.1 (for RHEL 5 Server) (RPMs)'

######################################################## Sync Repos
echo "Synching repos. This will take a lot of time..."
hammer product synchronize --name 'Red Hat Enterprise Linux Server' --organization "$ORG"

######################################################## Create Sync Plan
echo "Creating sync plan..."
hammer sync-plan create --name 'daily sync at 3 a.m.' \
--description 'A daily sync plans runs every morning a 3 a.m.' \
--enabled=true \
--interval daily \
--organization "$ORG" \
--sync-date '2015-04-15 03:00:00'

######################################################## Add products to sync plan
echo "Enabling sync plan..."
hammer product set-sync-plan --sync-plan 'daily sync at 3 a.m.' --organization ${ORG} --name "Red Hat Enterprise Linux Server"

######################################################## Lifecycle Environments
echo "Creating lifecycle environments..."
hammer lifecycle-environment create --name=dev  --prior Library --organization-label=${ORG}
hammer lifecycle-environment create --name=qas  --prior dev --organization-label=${ORG}
hammer lifecycle-environment create --name=prd  --prior qas --organization-label=${ORG}

######################################################## Add GPG Key
echo "Creating gpg key..."
hammer gpg create --key ${STAGEDIR}/RPM-GPG-KEY-smeyer --organization ${ORG} --name SMEYER

######################################################## Create Common Products
echo "Creating custom product..."
hammer product create --name "${ORG} COMMON" --organization-label=${ORG} --gpg-key SMEYER

######################################################## Common ${ORG} Products
echo "Creating custom repositories..."
((RHEL7)) && hammer repository create --content-type=yum --name=custom-common-rhel7-x86_64 --product="${ORG} COMMON" --organization-label=${ORG}
((RHEL6)) && hammer repository create --content-type=yum --name=custom-common-rhel6-x86_64 --product="${ORG} COMMON" --organization-label=${ORG}
((RHEL5)) && hammer repository create --content-type=yum --name=custom-common-rhel5-x86_64 --product="${ORG} COMMON" --organization-label=${ORG}
hammer repository create --content-type=puppet --name=custom-common-puppet --product="${ORG} COMMON" --organization-label=${ORG}

######################################################## Upload some Puppet modules to the common environment
echo "Uploading puppet module to common..."
hammer repository upload-content --organization ${ORG} --product="${ORG} COMMON" --name=custom-common-puppet --path ${STAGEDIR}/puppetlabs-stdlib-4.11.0.tar.gz

######################################################## Upload some RPM packages to the common environment
echo "Uploading rpm packages to common..."
((RHEL7)) && hammer repository upload-content --organization ${ORG} --product="${ORG} COMMON" --name=custom-common-rhel7-x86_64 --path ${STAGEDIR}/testpkg1-1.0.0-1.x86_64.rpm
((RHEL6)) && hammer repository upload-content --organization ${ORG} --product="${ORG} COMMON" --name=custom-common-rhel6-x86_64 --path ${STAGEDIR}/testpkg1-1.0.0-1.x86_64.rpm
((RHEL5)) && hammer repository upload-content --organization ${ORG} --product="${ORG} COMMON" --name=custom-common-rhel5-x86_64 --path ${STAGEDIR}/testpkg1-1.0.0-1.x86_64.rpm

######################################################## Create Content Views
echo "Creating common content views..."
((RHEL5)) && hammer content-view create --name "cv-common-os-rhel-5Server-x86_64" --description "RHEL Server 5 Core Build Content View" --organization ${ORG}
((RHEL6)) && hammer content-view create --name "cv-common-os-rhel-6Server-x86_64" --description "RHEL Server 6 Core Build Content View" --organization ${ORG}
((RHEL7)) && hammer content-view create --name "cv-common-os-rhel-7Server-x86_64" --description "RHEL Server 7 Core Build Content View" --organization ${ORG}
hammer content-view create --name "cv-common-custom-puppet" --description "Puppet Modules for all Countries" --organization ${ORG}

######################################################## Add Puppet Modules to Content Views
echo "Adding puppet modules to content view..."
hammer content-view puppet-module add --content-view cv-common-custom-puppet --name stdlib --organization ${ORG}

######################################################## Add repos to content views
echo "Adding repos to content views..."
((RHEL7)) && hammer content-view add-repository --organization "$ORG" \
--name "cv-common-os-rhel-7Server-x86_64" \
--repository 'Red Hat Enterprise Linux 7 Server RPMs x86_64 7Server' \
--product 'Red Hat Enterprise Linux Server'

((RHEL7)) && hammer content-view add-repository --organization "$ORG" \
--name "cv-common-os-rhel-7Server-x86_64" \
--repository 'Red Hat Satellite Tools 6.1 for RHEL 7 Server RPMs x86_64' \
--product 'Red Hat Enterprise Linux Server'

((RHEL6)) && hammer content-view add-repository --organization "$ORG" \
--name "cv-common-os-rhel-6Server-x86_64" \
--repository 'Red Hat Enterprise Linux 6 Server RPMs x86_64 6Server' \
--product 'Red Hat Enterprise Linux Server'

((RHEL6)) && hammer content-view add-repository --organization "$ORG" \
--name "cv-common-os-rhel-6Server-x86_64" \
--repository 'Red Hat Satellite Tools 6.1 for RHEL 6 Server RPMs x86_64' \
--product 'Red Hat Enterprise Linux Server'

((RHEL5)) && hammer content-view add-repository --organization "$ORG" \
--name "cv-common-os-rhel-5Server-x86_64" \
--repository 'Red Hat Enterprise Linux 5 Server RPMs x86_64 5Server' \
--product 'Red Hat Enterprise Linux Server'

((RHEL5)) && hammer content-view add-repository --organization "$ORG" \
--name "cv-common-os-rhel-5Server-x86_64" \
--repository 'Red Hat Satellite Tools 6.1 for RHEL 5 Server RPMs x86_64' \
--product 'Red Hat Enterprise Linux Server'

echo "Adding repositories to content views..." 
((RHEL5)) && hammer content-view add-repository --organization "$ORG" --name cv-common-os-rhel-5Server-x86_64 --repository custom-common-rhel5-x86_64 --product "${ORG} COMMON"
((RHEL6)) && hammer content-view add-repository --organization "$ORG" --name cv-common-os-rhel-6Server-x86_64 --repository custom-common-rhel6-x86_64 --product "${ORG} COMMON"
((RHEL7)) && hammer content-view add-repository --organization "$ORG" --name cv-common-os-rhel-7Server-x86_64 --repository custom-common-rhel7-x86_64 --product "${ORG} COMMON"

######################################################## publish content views
for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep '^cv-common'); do
	echo "Publishing content view $cv ..."
	hammer content-view publish --name $cv --organization ${ORG}
done

######################################################## create composite content views
echo "Creating composite content views..."
((RHEL7)) && hammer content-view create --name ccv-common-base-rhel-7Server-x86_64 --composite --description "Common CCV for base RHEL 7Server" --organization ${ORG} --component-ids $(get_cv cv-common-os-rhel-7Server-x86_64),$(get_cv cv-common-custom-puppet)
((RHEL6)) && hammer content-view create --name ccv-common-base-rhel-6Server-x86_64 --composite --description "Common CCV for base RHEL 6Server" --organization ${ORG} --component-ids $(get_cv cv-common-os-rhel-6Server-x86_64),$(get_cv cv-common-custom-puppet)
((RHEL5)) && hammer content-view create --name ccv-common-base-rhel-5Server-x86_64 --composite --description "Common CCV for base RHEL 5Server" --organization ${ORG} --component-ids $(get_cv cv-common-os-rhel-5Server-x86_64),$(get_cv cv-common-custom-puppet)

######################################################## create host collections
echo "Creating host collections..."
((RHEL7)) && hammer host-collection create --name dev-common-base-rhel-7Server-x86_64 --organization ${ORG}
((RHEL6)) && hammer host-collection create --name dev-common-base-rhel-6Server-x86_64 --organization ${ORG}
((RHEL5)) && hammer host-collection create --name dev-common-base-rhel-5Server-x86_64 --organization ${ORG}
((RHEL7)) && hammer host-collection create --name qas-common-base-rhel-7Server-x86_64 --organization ${ORG}
((RHEL6)) && hammer host-collection create --name qas-common-base-rhel-6Server-x86_64 --organization ${ORG}
((RHEL5)) && hammer host-collection create --name qas-common-base-rhel-5Server-x86_64 --organization ${ORG}
((RHEL7)) && hammer host-collection create --name prd-common-base-rhel-7Server-x86_64 --organization ${ORG}
((RHEL6)) && hammer host-collection create --name prd-common-base-rhel-6Server-x86_64 --organization ${ORG}
((RHEL5)) && hammer host-collection create --name prd-common-base-rhel-5Server-x86_64 --organization ${ORG}

######################################################## publish all composite content views
for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep '^ccv-'); do
	echo "Publishing composite content view $cv ..."
	hammer content-view publish --name $cv --organization ${ORG}
done

######################################################## promote all composite content views
for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep '^ccv-'); do
	echo "Promoting composite content view $cv lifecycle DEV..."
	hammer content-view version promote --content-view $cv --to-lifecycle-environment dev --organization ${ORG}

	echo "Promoting composite content view $cv lifecycle QAS..."
	hammer content-view version promote --content-view $cv --to-lifecycle-environment qas --organization ${ORG}
	
        echo "Promoting composite content view $cv lifecycle PRD..."
	hammer content-view version promote --content-view $cv --to-lifecycle-environment prd --organization ${ORG}
done

######################################################## create activation keys
echo "Creating activation keys..."
((RHEL7)) && hammer activation-key create --name act-dev-common-base-rhel-7Server-x86_64 --content-view ccv-common-base-rhel-7Server-x86_64 --lifecycle-environment dev --organization ${ORG}
((RHEL6)) && hammer activation-key create --name act-dev-common-base-rhel-6Server-x86_64 --content-view ccv-common-base-rhel-6Server-x86_64 --lifecycle-environment dev --organization ${ORG}
((RHEL5)) && hammer activation-key create --name act-dev-common-base-rhel-5Server-x86_64 --content-view ccv-common-base-rhel-5Server-x86_64 --lifecycle-environment dev --organization ${ORG}
((RHEL7)) && hammer activation-key create --name act-qas-common-base-rhel-7Server-x86_64 --content-view ccv-common-base-rhel-7Server-x86_64 --lifecycle-environment qas --organization ${ORG}
((RHEL6)) && hammer activation-key create --name act-qas-common-base-rhel-6Server-x86_64 --content-view ccv-common-base-rhel-6Server-x86_64 --lifecycle-environment qas --organization ${ORG}
((RHEL5)) && hammer activation-key create --name act-qas-common-base-rhel-5Server-x86_64 --content-view ccv-common-base-rhel-5Server-x86_64 --lifecycle-environment qas --organization ${ORG}
((RHEL7)) && hammer activation-key create --name act-prd-common-base-rhel-7Server-x86_64 --content-view ccv-common-base-rhel-7Server-x86_64 --lifecycle-environment prd --organization ${ORG}
((RHEL6)) && hammer activation-key create --name act-prd-common-base-rhel-6Server-x86_64 --content-view ccv-common-base-rhel-6Server-x86_64 --lifecycle-environment prd --organization ${ORG}
((RHEL5)) && hammer activation-key create --name act-prd-common-base-rhel-5Server-x86_64 --content-view ccv-common-base-rhel-5Server-x86_64 --lifecycle-environment prd  --organization ${ORG}

######################################################## add host collections
echo "Adding host collections to activation keys..."
((RHEL7)) && hammer activation-key add-host-collection --name act-dev-common-base-rhel-7Server-x86_64 --host-collection dev-common-base-rhel-7Server-x86_64 --organization ${ORG}
((RHEL6)) && hammer activation-key add-host-collection --name act-dev-common-base-rhel-6Server-x86_64 --host-collection dev-common-base-rhel-6Server-x86_64 --organization ${ORG}
((RHEL5)) && hammer activation-key add-host-collection --name act-dev-common-base-rhel-5Server-x86_64 --host-collection dev-common-base-rhel-5Server-x86_64 --organization ${ORG}
((RHEL7)) && hammer activation-key add-host-collection --name act-qas-common-base-rhel-7Server-x86_64 --host-collection qas-common-base-rhel-7Server-x86_64 --organization ${ORG}
((RHEL6)) && hammer activation-key add-host-collection --name act-qas-common-base-rhel-6Server-x86_64 --host-collection qas-common-base-rhel-6Server-x86_64 --organization ${ORG}
((RHEL5)) && hammer activation-key add-host-collection --name act-qas-common-base-rhel-5Server-x86_64 --host-collection qas-common-base-rhel-5Server-x86_64 --organization ${ORG}
((RHEL7)) && hammer activation-key add-host-collection --name act-prd-common-base-rhel-7Server-x86_64 --host-collection prd-common-base-rhel-7Server-x86_64 --organization ${ORG}
((RHEL6)) && hammer activation-key add-host-collection --name act-prd-common-base-rhel-6Server-x86_64 --host-collection prd-common-base-rhel-6Server-x86_64 --organization ${ORG}
((RHEL5)) && hammer activation-key add-host-collection --name act-prd-common-base-rhel-5Server-x86_64 --host-collection prd-common-base-rhel-5Server-x86_64 --organization ${ORG}

######################################################## add RHEL subscriptions
echo "Adding subscriptions to activation keys..."
((RHEL7)) && hammer activation-key add-subscription --name  act-dev-common-base-rhel-7Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL6)) && hammer activation-key add-subscription --name  act-dev-common-base-rhel-6Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL5)) && hammer activation-key add-subscription --name  act-dev-common-base-rhel-5Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL7)) && hammer activation-key add-subscription --name  act-qas-common-base-rhel-7Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL6)) && hammer activation-key add-subscription --name  act-qas-common-base-rhel-6Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL5)) && hammer activation-key add-subscription --name  act-qas-common-base-rhel-5Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL7)) && hammer activation-key add-subscription --name  act-prd-common-base-rhel-7Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL6)) && hammer activation-key add-subscription --name  act-prd-common-base-rhel-6Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
((RHEL5)) && hammer activation-key add-subscription --name  act-prd-common-base-rhel-5Server-x86_64 --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        

######################################################## Create common hostgroups
echo "Creating hostgroups..."
        ((RHEL7)) && hammer hostgroup create \
        --name dev-common-base-rhel-7Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-7Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 7.2" \
        --lifecycle-environment dev \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_7_Server_Kickstart_x86_64_7_2" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep dev_ccv_common_base_rhel_7Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL6)) && hammer hostgroup create \
        --name dev-common-base-rhel-6Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-6Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 6.7" \
        --lifecycle-environment dev \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_6_Server_Kickstart_x86_64_6_7" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep dev_ccv_common_base_rhel_6Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL5)) && hammer hostgroup create \
        --name dev-common-base-rhel-5Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-5Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 5.11" \
        --lifecycle-environment dev \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_5_Server_Kickstart_x86_64_5_11" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep dev_ccv_common_base_rhel_5Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL7)) && hammer hostgroup create \
        --name qas-common-base-rhel-7Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-7Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 7.2" \
        --lifecycle-environment qas \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_7_Server_Kickstart_x86_64_7_2" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep qas_ccv_common_base_rhel_7Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL6)) && hammer hostgroup create \
        --name qas-common-base-rhel-6Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-6Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 6.7" \
        --lifecycle-environment qas \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_6_Server_Kickstart_x86_64_6_7" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep qas_ccv_common_base_rhel_6Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL5)) && hammer hostgroup create \
        --name qas-common-base-rhel-5Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-5Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 5.11" \
        --lifecycle-environment qas \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_5_Server_Kickstart_x86_64_5_11" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep qas_ccv_common_base_rhel_5Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL7)) && hammer hostgroup create \
        --name prd-common-base-rhel-7Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-7Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 7.2" \
        --lifecycle-environment prd \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_7_Server_Kickstart_x86_64_7_2" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep prd_ccv_common_base_rhel_7Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL6)) && hammer hostgroup create \
        --name prd-common-base-rhel-6Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-6Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 6.7" \
        --lifecycle-environment prd \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_6_Server_Kickstart_x86_64_6_7" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep prd_ccv_common_base_rhel_6Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL5)) && hammer hostgroup create \
        --name prd-common-base-rhel-5Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-common-base-rhel-5Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 5.11" \
        --lifecycle-environment prd \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_5_Server_Kickstart_x86_64_5_11" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep prd_ccv_common_base_rhel_5Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')


######################################################## Add activation keys to common hostgroups
echo "Adding activation keys to hostgroups..."
((RHEL7)) && hammer hostgroup set-parameter --hostgroup dev-common-base-rhel-7Server-x86_64 --name "kt_activation_keys" --value "act-dev-common-base-rhel-7Server-x86_64"
((RHEL6)) && hammer hostgroup set-parameter --hostgroup dev-common-base-rhel-6Server-x86_64 --name "kt_activation_keys" --value "act-dev-common-base-rhel-6Server-x86_64"
((RHEL5)) && hammer hostgroup set-parameter --hostgroup dev-common-base-rhel-5Server-x86_64 --name "kt_activation_keys" --value "act-dev-common-base-rhel-5Server-x86_64"
((RHEL7)) && hammer hostgroup set-parameter --hostgroup qas-common-base-rhel-7Server-x86_64 --name "kt_activation_keys" --value "act-qas-common-base-rhel-7Server-x86_64"
((RHEL6)) && hammer hostgroup set-parameter --hostgroup qas-common-base-rhel-6Server-x86_64 --name "kt_activation_keys" --value "act-qas-common-base-rhel-6Server-x86_64"
((RHEL5)) && hammer hostgroup set-parameter --hostgroup qas-common-base-rhel-5Server-x86_64 --name "kt_activation_keys" --value "act-qas-common-base-rhel-5Server-x86_64"
((RHEL7)) && hammer hostgroup set-parameter --hostgroup prd-common-base-rhel-7Server-x86_64 --name "kt_activation_keys" --value "act-prd-common-base-rhel-7Server-x86_64"
((RHEL6)) && hammer hostgroup set-parameter --hostgroup prd-common-base-rhel-6Server-x86_64 --name "kt_activation_keys" --value "act-prd-common-base-rhel-6Server-x86_64"
((RHEL5)) && hammer hostgroup set-parameter --hostgroup prd-common-base-rhel-5Server-x86_64 --name "kt_activation_keys" --value "act-prd-common-base-rhel-5Server-x86_64"

echo "Creating country specific stuff..."
######################################################## Country Loop
for COUNTRY in ${COUNTRIES}; do

        # Create upper and lower case variables for country
        COUNTRY_LC=$(echo ${COUNTRY} | tr '[:upper:]' '[:lower:]')
        COUNTRY_UC=$(echo ${COUNTRY} | tr '[:lower:]' '[:upper:]')

        echo "Starting with country code ${COUNTRY_UC}..."

        ######################################################## Country Products
        echo "Creating products..."
        hammer product create --name "${ORG} ${COUNTRY_UC}" --organization-label=${ORG} --gpg-key SMEYER

        ######################################################## Country Repositories
        echo "Creating repositories..."
        ((RHEL5)) && hammer repository create --content-type=yum --name=custom-${COUNTRY_LC}-rhel5-x86_64 --product="${ORG} ${COUNTRY_UC}" --organization-label=${ORG}
        ((RHEL6)) && hammer repository create --content-type=yum --name=custom-${COUNTRY_LC}-rhel6-x86_64 --product="${ORG} ${COUNTRY_UC}" --organization-label=${ORG}
        ((RHEL7)) && hammer repository create --content-type=yum --name=custom-${COUNTRY_LC}-rhel7-x86_64 --product="${ORG} ${COUNTRY_UC}" --organization-label=${ORG}
        hammer repository create --content-type=puppet --name=custom-${COUNTRY_LC}-puppet --product="${ORG} ${COUNTRY_UC}" --organization-label=${ORG}

        ######################################################## Upload some Puppet modules
        echo "Uploading puppet modules..."
        hammer repository upload-content --organization ${ORG} --product="${ORG} ${COUNTRY_UC}" --name=custom-${COUNTRY_LC}-puppet --path ${STAGEDIR}/puppetlabs-motd-1.4.0.tar.gz

        ######################################################## Upload some Puppet modules
        echo "Uploading rpm packages..."
        ((RHEL7)) && hammer repository upload-content --organization ${ORG} --product="${ORG} ${COUNTRY_UC}" --name=custom-${COUNTRY_LC}-rhel7-x86_64 --path ${STAGEDIR}/testpkg2-1.0.0-1.x86_64.rpm
        ((RHEL6)) && hammer repository upload-content --organization ${ORG} --product="${ORG} ${COUNTRY_UC}" --name=custom-${COUNTRY_LC}-rhel6-x86_64 --path ${STAGEDIR}/testpkg2-1.0.0-1.x86_64.rpm
        ((RHEL5)) && hammer repository upload-content --organization ${ORG} --product="${ORG} ${COUNTRY_UC}" --name=custom-${COUNTRY_LC}-rhel5-x86_64 --path ${STAGEDIR}/testpkg2-1.0.0-1.x86_64.rpm

        ######################################################## Create Content Views
        echo "Creating content views..."
        ((RHEL7)) && hammer content-view create --name "cv-${COUNTRY_LC}-custom-rhel-7Server-x86_64" --description "RHEL Server 7 Custom Packages for Country ${COUNTRY_UC}" --organization ${ORG}
        ((RHEL6)) && hammer content-view create --name "cv-${COUNTRY_LC}-custom-rhel-6Server-x86_64" --description "RHEL Server 6 Custom Packages for Country ${COUNTRY_UC}" --organization ${ORG}
        ((RHEL5)) && hammer content-view create --name "cv-${COUNTRY_LC}-custom-rhel-5Server-x86_64" --description "RHEL Server 5 Custom Packages for Country ${COUNTRY_UC}" --organization ${ORG}
        hammer content-view create --name "cv-${COUNTRY_LC}-custom-puppet" --description "Puppet Modules for Country ${COUNTRY_UC}" --organization ${ORG}

        ######################################################## Add Puppet Modules to Content Views
        echo "Adding puppet modules to content views..."
        hammer content-view puppet-module add --content-view cv-${COUNTRY_LC}-custom-puppet --name motd --organization ${ORG}

        echo "Adding rpm packages to content views ..."
        ((RHEL5)) && hammer content-view add-repository --organization "$ORG" --name cv-${COUNTRY_LC}-custom-rhel-5Server-x86_64 --repository custom-${COUNTRY_LC}-rhel5-x86_64 --product "${ORG} ${COUNTRY_UC}"
        ((RHEL6)) && hammer content-view add-repository --organization "$ORG" --name cv-${COUNTRY_LC}-custom-rhel-6Server-x86_64 --repository custom-${COUNTRY_LC}-rhel6-x86_64 --product "${ORG} ${COUNTRY_UC}"
        ((RHEL7)) && hammer content-view add-repository --organization "$ORG" --name cv-${COUNTRY_LC}-custom-rhel-7Server-x86_64 --repository custom-${COUNTRY_LC}-rhel7-x86_64 --product "${ORG} ${COUNTRY_UC}"

        ######################################################## publish content views
        echo "Publishing content views..."
        for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep "^cv-${COUNTRY_LC}"); do
	        echo "Publishing content view $cv ..."
	        hammer content-view publish --name $cv --organization ${ORG}
        done

        ######################################################## create composite content views
        echo "Creating composite content views..."
        ((RHEL7)) && hammer content-view create --name ccv-${COUNTRY_LC}-base-rhel-7Server-x86_64 --composite --description "Common CCV for base RHEL 7Server Country ${COUNTRY_UC}" --organization ${ORG} --component-ids $(get_cv cv-common-os-rhel-7Server-x86_64),$(get_cv cv-common-custom-puppet),$(get_cv cv-${COUNTRY_LC}-custom-rhel-7Server-x86_64),$(get_cv cv-${COUNTRY_LC}-custom-puppet)
        ((RHEL6)) && hammer content-view create --name ccv-${COUNTRY_LC}-base-rhel-6Server-x86_64 --composite --description "Common CCV for base RHEL 6Server Country ${COUNTRY_UC}" --organization ${ORG} --component-ids $(get_cv cv-common-os-rhel-6Server-x86_64),$(get_cv cv-common-custom-puppet),$(get_cv cv-${COUNTRY_LC}-custom-rhel-6Server-x86_64),$(get_cv cv-${COUNTRY_LC}-custom-puppet)
        ((RHEL5)) && hammer content-view create --name ccv-${COUNTRY_LC}-base-rhel-5Server-x86_64 --composite --description "Common CCV for base RHEL 5Server Country ${COUNTRY_UC}" --organization ${ORG} --component-ids $(get_cv cv-common-os-rhel-5Server-x86_64),$(get_cv cv-common-custom-puppet),$(get_cv cv-${COUNTRY_LC}-custom-rhel-5Server-x86_64),$(get_cv cv-${COUNTRY_LC}-custom-puppet)
        
        ######################################################## publish all composite content views
        for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep "^ccv-${COUNTRY_LC}"); do
	        echo "Publishing composite content view $cv ..."
	        hammer content-view publish --name $cv --organization ${ORG}
        done

        ######################################################## promote all composite content views
        for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep "^ccv-${COUNTRY_LC}"); do
	        echo "Promoting composite content view $cv lifecycle DEV..."
	        hammer content-view version promote --content-view $cv --to-lifecycle-environment dev --organization ${ORG}

	        echo "Promoting composite content view $cv lifecycle QAS..."
	        hammer content-view version promote --content-view $cv --to-lifecycle-environment qas --organization ${ORG}
	
                echo "Promoting composite content view $cv lifecycle PRD..."
	        hammer content-view version promote --content-view $cv --to-lifecycle-environment prd --organization ${ORG}
        done

        ######################################################## create host collections
        ((RHEL7)) && hammer host-collection create --name dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 --organization ${ORG}
        ((RHEL6)) && hammer host-collection create --name dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 --organization ${ORG}
        ((RHEL5)) && hammer host-collection create --name dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 --organization ${ORG}
        ((RHEL7)) && hammer host-collection create --name qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 --organization ${ORG}
        ((RHEL6)) && hammer host-collection create --name qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 --organization ${ORG}
        ((RHEL5)) && hammer host-collection create --name qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 --organization ${ORG}
        ((RHEL7)) && hammer host-collection create --name prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 --organization ${ORG}
        ((RHEL6)) && hammer host-collection create --name prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 --organization ${ORG}
        ((RHEL5)) && hammer host-collection create --name prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 --organization ${ORG}
        

        ######################################################## create activation keys
        echo "Creating activation keys..."
        ((RHEL7)) && hammer activation-key create --name act-dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-7Server-x86_64 --lifecycle-environment dev --organization ${ORG}
        ((RHEL6)) && hammer activation-key create --name act-dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-6Server-x86_64 --lifecycle-environment dev --organization ${ORG}
        ((RHEL5)) && hammer activation-key create --name act-dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-5Server-x86_64 --lifecycle-environment dev --organization ${ORG}
        ((RHEL7)) && hammer activation-key create --name act-qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-7Server-x86_64 --lifecycle-environment qas --organization ${ORG}
        ((RHEL6)) && hammer activation-key create --name act-qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-6Server-x86_64 --lifecycle-environment qas --organization ${ORG}
        ((RHEL5)) && hammer activation-key create --name act-qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-5Server-x86_64 --lifecycle-environment qas --organization ${ORG}
        ((RHEL7)) && hammer activation-key create --name act-prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-7Server-x86_64 --lifecycle-environment prd --organization ${ORG}
        ((RHEL6)) && hammer activation-key create --name act-prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-6Server-x86_64 --lifecycle-environment prd --organization ${ORG}
        ((RHEL5)) && hammer activation-key create --name act-prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 --content-view ccv-${COUNTRY_LC}-base-rhel-5Server-x86_64 --lifecycle-environment prd --organization ${ORG}

        ######################################################## add host collections
        echo "Adding host collections to activation keys..."
        ((RHEL7)) && hammer activation-key add-host-collection --name act-dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 --host-collection dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-host-collection --name act-dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 --host-collection dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-host-collection --name act-dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 --host-collection dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 --organization ${ORG}
        ((RHEL7)) && hammer activation-key add-host-collection --name act-qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 --host-collection qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-host-collection --name act-qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 --host-collection qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-host-collection --name act-qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 --host-collection qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 --organization ${ORG}
        ((RHEL7)) && hammer activation-key add-host-collection --name act-prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 --host-collection prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-host-collection --name act-prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 --host-collection prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-host-collection --name act-prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 --host-collection prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 --organization ${ORG}
        
        ######################################################## add RHEL subscriptions
        ((RHEL7)) && hammer activation-key add-subscription --name  act-dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-subscription --name  act-dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-subscription --name  act-dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL7)) && hammer activation-key add-subscription --name  act-qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-subscription --name  act-qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-subscription --name  act-qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL7)) && hammer activation-key add-subscription --name  act-prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-subscription --name  act-prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-subscription --name  act-prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep -i '^Red Hat Enterprise Linux' | awk -F',' '{print $8}') --organization ${ORG}
        
        ######################################################## add country subscriptions
        ((RHEL7)) && hammer activation-key add-subscription --name  act-dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-subscription --name  act-dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-subscription --name  act-dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL7)) && hammer activation-key add-subscription --name  act-qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-subscription --name  act-qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-subscription --name  act-qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL7)) && hammer activation-key add-subscription --name  act-prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL6)) && hammer activation-key add-subscription --name  act-prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        ((RHEL5)) && hammer activation-key add-subscription --name  act-prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
                --subscription-id $(hammer --csv subscription list --organization ${ORG} | grep ${COUNTRY_UC} | awk -F',' '{print $8}') --organization ${ORG}
        
        ######################################################## Create common hostgroups
        echo "Creating hostgroups..."
        ((RHEL7)) && hammer hostgroup create \
        --name dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 7.2" \
        --lifecycle-environment dev \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_7_Server_Kickstart_x86_64_7_2" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep dev_ccv_${COUNTRY_LC}_base_rhel_7Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL6)) && hammer hostgroup create \
        --name dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 6.7" \
        --lifecycle-environment dev \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_6_Server_Kickstart_x86_64_6_7" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep dev_ccv_${COUNTRY_LC}_base_rhel_6Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL5)) && hammer hostgroup create \
        --name dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 5.11" \
        --lifecycle-environment dev \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_5_Server_Kickstart_x86_64_5_11" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep dev_ccv_${COUNTRY_LC}_base_rhel_5Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL7)) && hammer hostgroup create \
        --name qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 7.2" \
        --lifecycle-environment qas \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_7_Server_Kickstart_x86_64_7_2" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep qas_ccv_${COUNTRY_LC}_base_rhel_7Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL6)) && hammer hostgroup create \
        --name qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 6.7" \
        --lifecycle-environment qas \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_6_Server_Kickstart_x86_64_6_7" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep qas_ccv_${COUNTRY_LC}_base_rhel_6Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL5)) && hammer hostgroup create \
        --name qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 5.11" \
        --lifecycle-environment qas \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_5_Server_Kickstart_x86_64_5_11" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep qas_ccv_${COUNTRY_LC}_base_rhel_5Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL7)) && hammer hostgroup create \
        --name prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-7Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 7.2" \
        --lifecycle-environment prd \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_7_Server_Kickstart_x86_64_7_2" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep prd_ccv_${COUNTRY_LC}_base_rhel_7Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL6)) && hammer hostgroup create \
        --name prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-6Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 6.7" \
        --lifecycle-environment prd \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_6_Server_Kickstart_x86_64_6_7" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep prd_ccv_${COUNTRY_LC}_base_rhel_6Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')

        ((RHEL5)) && hammer hostgroup create \
        --name prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
        --organizations ${ORG} \
        --content-view ccv-${COUNTRY_LC}-base-rhel-5Server-x86_64 \
        --architecture x86_64 \
        --operatingsystem "RHEL Server 5.11" \
        --lifecycle-environment prd \
        --locations ${LOC} \
        --medium "${ORG}/Library/Red_Hat_Server/Red_Hat_Enterprise_Linux_5_Server_Kickstart_x86_64_5_11" \
        --partition-table "Kickstart default" \
        --puppet-ca-proxy ${SATHOST} \
        --puppet-proxy ${SATHOST} \
        --content-source-id 1 \
        --puppet-classes access_insights_client \
        --environment $(hammer --csv environment list | grep prd_ccv_${COUNTRY_LC}_base_rhel_5Server_x86_64 | grep ${ORG} | awk -F"," '{print $2}')


        ######################################################## Add activation keys to common hostgroups
        echo "Adding activation keys to hostgroups..."
        ((RHEL7)) && hammer hostgroup set-parameter --hostgroup dev-${COUNTRY_LC}-base-rhel-7Server-x86_64 --name "kt_activation_keys" --value "act-dev-${COUNTRY_LC}-base-rhel-7Server-x86_64"
        ((RHEL6)) && hammer hostgroup set-parameter --hostgroup dev-${COUNTRY_LC}-base-rhel-6Server-x86_64 --name "kt_activation_keys" --value "act-dev-${COUNTRY_LC}-base-rhel-6Server-x86_64"
        ((RHEL5)) && hammer hostgroup set-parameter --hostgroup dev-${COUNTRY_LC}-base-rhel-5Server-x86_64 --name "kt_activation_keys" --value "act-dev-${COUNTRY_LC}-base-rhel-5Server-x86_64"
        ((RHEL7)) && hammer hostgroup set-parameter --hostgroup qas-${COUNTRY_LC}-base-rhel-7Server-x86_64 --name "kt_activation_keys" --value "act-qas-${COUNTRY_LC}-base-rhel-7Server-x86_64"
        ((RHEL6)) && hammer hostgroup set-parameter --hostgroup qas-${COUNTRY_LC}-base-rhel-6Server-x86_64 --name "kt_activation_keys" --value "act-qas-${COUNTRY_LC}-base-rhel-6Server-x86_64"
        ((RHEL5)) && hammer hostgroup set-parameter --hostgroup qas-${COUNTRY_LC}-base-rhel-5Server-x86_64 --name "kt_activation_keys" --value "act-qas-${COUNTRY_LC}-base-rhel-5Server-x86_64"
        ((RHEL7)) && hammer hostgroup set-parameter --hostgroup prd-${COUNTRY_LC}-base-rhel-7Server-x86_64 --name "kt_activation_keys" --value "act-prd-${COUNTRY_LC}-base-rhel-7Server-x86_64"
        ((RHEL6)) && hammer hostgroup set-parameter --hostgroup prd-${COUNTRY_LC}-base-rhel-6Server-x86_64 --name "kt_activation_keys" --value "act-prd-${COUNTRY_LC}-base-rhel-6Server-x86_64"
        ((RHEL5)) && hammer hostgroup set-parameter --hostgroup prd-${COUNTRY_LC}-base-rhel-5Server-x86_64 --name "kt_activation_keys" --value "act-prd-${COUNTRY_LC}-base-rhel-5Server-x86_64"

        # end country loop
done



########################################################
# TODO BIG LIST OF STUFF TO ADD
# make RHEL versions selectable
# create locations?
# create user groups for each country
# create users for each country
# add 3rd party products, gpg keys, repos, cvs
# set some global parameters
# create config groups
# add scap content









