#!/bin/bash
export ORG=XXX

# update content views
for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep '^cv-'); do
        echo "Publishing content view $cv ..."
        hammer content-view publish --name $cv --organization ${ORG}
done

echo "Updating composite content views..."
for ccv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep '^ccv-'); do
        cvids=""
        echo "Get embedded CVs for ${ccv}..."
        for cv in $( hammer content-view info --name $ccv --organization ${ORG} | grep " cv-" | awk -F" " '{print $2}'); do
                
                echo "Getting newest version of embedded cv ${cv}..."
                newestver=$(hammer --csv content-view version list --content-view $cv --organization ${ORG} | grep -v Version | sort -rn | awk -F"," 'NR==1{print $3}')

                echo "Getting id of CV $cv version ${newestver}..." 
                cvid=$(hammer --csv content-view version list --content-view $cv --organization ${ORG} | grep ",${newestver},"| awk -F"," '{print $1}')

                # collect all cv ids to add to the ccv
                cvids="${cvids},${cvid}"
        done


        # set ccv to use newest version of embedded cv
        echo "Updating CV versions (${cvids}) of CCV ${ccv}..."
        hammer content-view update --name $ccv --organization ${ORG} --component-ids ${cvids}

        echo "Publishing composite content view ${ccv}..."
        hammer content-view publish --name $ccv --organization ${ORG}
done

# promote all composite content views
echo "Promoting all Composite Content Views..."
for ccv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep '^ccv-'); do

        version=$(hammer --csv content-view version list --content-view ${ccv} --organization ${ORG} | grep -v Version | sort -rn | awk -F"," 'NR==1{print $3}')

        echo "Promoting composite content view $ccv lifecycle DEV..."
        hammer content-view version promote --content-view $ccv --to-lifecycle-environment dev --organization ${ORG} --version ${version}

        echo "Promoting composite content view $ccv lifecycle QAS..."
        hammer content-view version promote --content-view $ccv --to-lifecycle-environment qas --organization ${ORG} --version ${version}

        echo "Promoting composite content view $ccv lifecycle PRD..."
        hammer content-view version promote --content-view $ccv --to-lifecycle-environment prd --organization ${ORG} --version ${version}
done

echo "Done. Exiting, isn't it?"

