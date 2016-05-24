#!/bin/bash
export ORG=XXX

# update content views
for cv in $(hammer --csv content-view list --organization ${ORG}| grep -vi '^Content View ID,' | awk -F',' '{print $2}' | grep puppet); do
    echo "Publishing content view $cv ..."
    hammer content-view publish --name $cv --organization ${ORG}
done
