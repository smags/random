
# Foreman / Katello advanced reporting 

I created this little guide to get some better reporting from our Foreman server. We use dbfacephp to create the reports but any other reporting engine like Jasper Reports should work too.

I added some pictures of our reporting to the repository to give you an impression.

All commands were tested against a Foreman 1.8.0 server on RHEL6 and Katello 2.2 RC3 server on RHEL7. The database was Postgres v8.4 on RHEL6 and v9.2 on RHEL7. Differences in the required commands are highlighted in **bold**.

For Debian systems you might have some different package names and paths.
If you have more information for Debian, feel free to send me a pull request.

## Installing Tablefunc

First we need the tablefunc.sql to create postgresql crosstab (aka pivot) queries. As root you have to install postgresql-contrib

```
yum install postgresql-contrib
```

Switch to postgres DB user

```
su - postgres
```

Create the tablefunc function (**only on Postgres 8.4**)

```
psql -d foreman -f /usr/share/pgsql/contrib/tablefunc.sql
```

Start psql admin tool

```
psql
```


Connect to foreman database

```
postgres=# \c foreman
```

Create extension for crosstab queries (**only Postgres 9.2**)

```
postgres=# CREATE EXTENSION tablefunc;
```

## Create a ReadOnly user and configure access rights

Create role/user "readonly" with a password of "fluffy"

```
postgres=# create role readonly login password 'fluffy';
```

Allow the user to connect to the db

```
postgres=# grant connect on database foreman to readonly;
```

Allow the user to see the public schema, required to even see all the tables

```
postgres=# grant usage on schema public to readonly;
```

Allow the user to read from selected tables

```
postgres=# grant select on environments,reports,host_classes,puppetclasses,fact_values,hostgroups,hosts,fact_names,parameters to readonly;
```

## Configure remote connections

If your reporting system is on another host, you need to allow the user to connect from other hosts.

```
vim /var/lib/pgsql/data/pg_hba.conf
```
And add this line to the file:
```
host     all     readonly   	0.0.0.0/0       md5
```

```
vim /var/lib/pgsql/data/postgresql.conf
```

Replace ```listen_addresses = 'localhost'``` with ```listen_addresses = '*'```


** Warning! katello-installer/foreman-installer will add this entry
at the end of the file when you configure katello or foreman.
Ignore the commented entry at the top of the file and scoll down.**

## Restart postgres and test the connection

```
service postgresql restart
```
And a final connection test:
  
```
sql -h $(hostname) -U readonly -W foreman
```

## Tools to consider...
To test some sql queries you can install PGAdmin from [PGAdmin](http://www.pgadmin.org) or use the command line.

If you prefer the command line here is what you need to do.

If you connect from a remote system, install ```psql```.

Copy some of the example queries to a file on your system and run the query with the command

```
psql -h katello -U readonly -W foreman -f test.sql
Password for user readonly:
       Hostname        | Kernel Version | Uptime in Hours
-----------------------+----------------+-----------------
 c7test03.somedomain   | 3.10.0         | 32
 c7test04.somedomain   | 3.10.0         | 31
 katello.somedomain    | 3.10.0         | 35
 r6test15.somedomain   | 2.6.32         | 35
 r7test15.somedomain   | 3.10.0         | 35
 r7test16.somedomain   | 3.10.0         | 35
(6 rows) 
```


## Some sample sql queries

Get uptime for all hosts:
  
``` sql
SELECT 
  hosts.name AS Hostname, 
  fact_values.value AS content
FROM 
  public.hosts, 
  public.fact_names, 
  public.fact_values
WHERE 
  fact_values.host_id = hosts.id AND
  fact_values.fact_name_id = fact_names.id AND
  fact_names.name = 'uptime_days'
ORDER BY
  hosts.name ASC;
```


Count by kernel release:

``` sql
SELECT 
  count(*),
  fact_values.value
FROM 
  public.hosts, 
  public.fact_names, 
  public.fact_values
WHERE 
  fact_values.host_id = hosts.id AND
  fact_values.fact_name_id = fact_names.id AND
  fact_names.name = 'kernelrelease'
GROUP by fact_values.value;
```



Memory Summary (all systems):
  
``` sql
SELECT 
  round(SUM(fact_values.value::float::numeric /1024))
FROM 
  public.fact_names, 
  public.fact_values
WHERE 
  fact_values.fact_name_id = fact_names.id AND
  fact_names.name = 'memorysize_mb';
```

Get environment of all systems:

``` sql
SELECT 
  environments.name,
  count(*)
FROM 
  public.hosts, 
  public.environments
WHERE 
  hosts.environment_id = environments.id
GROUP by environments.name;
```

Lets get some host parameters. To get more than one 
parameter we have to create a pivot table, postgres 
uses the name crosstab for it.  

``` sql
SELECT DISTINCT * FROM crosstab(
  'SELECT 
  hosts.name AS hostname, 
  parameters.name AS param,
  parameters.value AS content
FROM 
  public.hosts, 
  public.parameters
WHERE 
  parameters.reference_id = hosts.id AND
  (
                parameters.name = ''test1'' OR 
                parameters.name = ''test2''
  ) 
  
  ORDER by 1;'
  ,$$SELECT unnest('{
                test1,
                test2
  }'::text[])$$)    
AS ct         
  ( 
                "Hostname" text,
                "Test 1" text, 
                "Test 2" text

  )
ORDER by "Hostname";
```


And some facts:

``` sql
SELECT DISTINCT * FROM crosstab(
  'SELECT 
  hosts.name AS hostname, 
  fact_names.name AS fact,
  fact_values.value AS content
FROM 
  public.hosts, 
  public.fact_names, 
  public.fact_values
WHERE 
  fact_values.host_id = hosts.id AND
  fact_values.fact_name_id = fact_names.id AND
  (                
                fact_names.name = ''kernelversion'' OR 
                fact_names.name = ''uptime_hours''
  ) 
  
  ORDER by 1;'
  ,$$SELECT unnest('{
                kernelversion,
                uptime_hours
  }'::text[])$$)    
AS ct         
  (
                "Hostname" text,
                "Kernel Version" text, 
                "Uptime in Hours" text

  )
  ORDER by "Hostname";
```

**A more advanced DB2 list that wouldn’t work in your environment.**

Just to give you some examples to play with…

``` sql
SELECT * FROM ( 
 SELECT DISTINCT * FROM crosstab( 
  'SELECT  
  hosts.name AS hostname,  
  fact_names.name AS fact, 
  fact_values.value AS content 
FROM  
  public.hosts,  
  public.fact_names,  
  public.fact_values 
WHERE  
  fact_values.host_id = hosts.id AND 
  fact_values.fact_name_id = fact_names.id AND 
  (                 
                fact_names.name = ''stage_os'' OR  
                fact_names.name = ''gis_country_name'' OR 
                fact_names.name = ''customer_id'' OR 
                fact_names.name = ''costcenter'' OR 
                fact_names.name = ''application'' OR 
                fact_names.name = ''operatingsystem'' OR 
                fact_names.name = ''system_release'' OR 
                fact_names.name = ''virtual'' OR 
                fact_names.name = ''processor0'' OR 
                fact_names.name = ''processorcount'' OR 
                fact_names.name = ''physicalprocessorcount'' OR 
                fact_names.name = ''memorytotal'' OR 
                fact_names.name = ''gis_db2_level_105'' OR 
                fact_names.name = ''gis_db2_identifier_105'' OR 
                fact_names.name = ''gis_db2_expiry_105'' OR 
                fact_names.name = ''gis_db2_level_97'' OR 
                fact_names.name = ''gis_db2_identifier_97'' OR          
                fact_names.name = ''gis_db2_expiry_97'' OR 
                fact_names.name = ''gis_db2_level_95'' OR 
                fact_names.name = ''gis_db2_identifier_95'' OR          
                fact_names.name = ''gis_db2_expiry_95'' 
  )  
   
  ORDER by 1;' 
  ,$$SELECT unnest('{ 
                stage_os, 
                gis_country_name, 
                customer_id, 
                costcenter, 
                application, 
                operatingsystem, 
                system_release, 
                virtual, 
                processor0, 
                processorcount, 
                physicalprocessorcount, 
                memorytotal, 
                gis_db2_level_105, 
                gis_db2_identifier_105, 
                gis_db2_expiry_105, 
                gis_db2_level_97, 
                gis_db2_identifier_97, 
                gis_db2_expiry_97, 
                gis_db2_level_95, 
                gis_db2_identifier_95, 
                gis_db2_expiry_95 
  
                 
  }'::text[])$$)     
AS ct          
  (                -- These are the collum names 
                "Hostname" text,  
                "Stage" text, 
                "Country" text,  
                "Customer" text, 
                "KLV" text,  
                "Application" text, 
                "OS" text,  
                "Release" text, 
                "HW - VM" text, 
                "CPU Type" text, 
                "Cores" text, 
                "CPU" text, 
                "Memory" text, 
                "v10.5 Version" text, 
                "v10.5 Lic" text, 
                "v10.5 Exp" text, 
                "v9.7 Version" text, 
                "v9.7 Lic" text, 
                "v9.7 Exp" text, 
                "v9.5 Version" text, 
                "v9.5 Lic" text, 
                "v9.5 Exp" text 
  ) 
ORDER by "Hostname" 
) AS db2select 
 
WHERE  
        "v10.5 Lic" IS NOT NULL OR 
        "v9.7 Lic" IS NOT NULL OR 
        "v9.5 Lic" IS NOT NULL;
```
 
 
