#!/bin/bash

echo "Deleting old content view versions..."

for i in $(hammer --csv content-view version list | grep "\"\"" | awk -F"," '{print $1}'); do hammer content-view version delete --id $i; done

echo "Done!"

