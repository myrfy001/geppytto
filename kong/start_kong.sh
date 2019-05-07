#! /bin/bash

export KONG_DATABASE=off
export KONG_PROXY_LISTEN='0.0.0.0:11000, 0.0.0.0:11443 ssl'
export KONG_ADMIN_LISTEN='0.0.0.0:11001, 0.0.0.0:11444 ssl'
export KONG_PLUGINS='bundled,geppytto_dynamic_router'
export KONG_DECLARATIVE_CONFIG=dbless_kong.yml

cp -rT ./geppytto_dynamic_router /usr/local/share/lua/5.1/kong/plugins/geppytto_dynamic_router
cp -r ./dbless_kong.yml /

/usr/local/bin/kong stop
/usr/local/bin/kong start