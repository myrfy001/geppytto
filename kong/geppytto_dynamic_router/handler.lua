local cjson = require "cjson"

-- Extending the Base Plugin handler is optional, as there is no real
-- concept of interface in Lua, but the Base Plugin handler's methods
-- can be called from your child implementation and will print logs
-- in your `error.log` file (where all logs are printed).
local BasePlugin = require "kong.plugins.base_plugin"
local CustomHandler = BasePlugin:extend()

-- Your plugin handler's constructor. If you are extending the
-- Base Plugin handler, it's only role is to instantiate itself
-- with a name. The name is your plugin name as it will be printed in the logs.
function CustomHandler:new()
  CustomHandler.super.new(self, "geppytto_dynamic_router")
end

function CustomHandler:init_worker()
  -- Eventually, execute the parent implementation
  -- (will log that your plugin is entering this context)
  CustomHandler.super.init_worker(self)

  -- Implement any custom logic here
end

function CustomHandler:certificate(config)
  -- Eventually, execute the parent implementation
  -- (will log that your plugin is entering this context)
  CustomHandler.super.certificate(self)

  -- Implement any custom logic here
end

function CustomHandler:rewrite(config)
  -- Eventually, execute the parent implementation
  -- (will log that your plugin is entering this context)
  CustomHandler.super.rewrite(self)

  -- Implement any custom logic here
end

function CustomHandler:access(config)
  -- Eventually, execute the parent implementation
  -- (will log that your plugin is entering this context)
  CustomHandler.super.access(self)

  local bid_match, err = ngx.re.match(ngx.var.request_uri, [[/devtools/browser/([-a-zA-Z0-9_]+)]], 'o')
  if bid_match then
    bid = bid_match[1]
  else
    ngx.log(ngx.ERR, "missing bid")
    return
  end

  local query = {['bid'] = bid}

  local access_token = kong.request.get_query_arg('access_token')
  if access_token then
    query['access_token'] = access_token
  else
    query['access_token'] = kong.request.get_header["X-GEPPYTTO-ACCESS-TOKEN"]
  end

  if ngx.var.browser_name then
    query['browser_name'] = ngx.var.browser_name
  end

  local http = require "resty.http"
  local httpc = http.new()
  local res, err = httpc:request_uri(config.dynamic_route_service_url, {
    method = "GET",
    query = query,
    headers = {
      ["Content-Type"] = "application/json",
    },
    keepalive_timeout = 60,
    keepalive_pool = 10
  })

  if err then
    ngx.log(ngx.ERR, "Request Auth Service Error")
    ngx.log(ngx.ERR, err)
  end

  ngx.log(ngx.ERR, 'dynamic_reply-------------')
  ngx.log(ngx.ERR, res.body)
  if not res then
    ngx.log(ngx.ERR, "Request Auth Service Error")
    return kong.response.exit(500, { message = "An unexpected error occurred"})
  end

  local upstream_info = cjson.decode(res.body)

  if upstream_info.code ~= 200 then
    return kong.response.exit(upstream_info.code, {message = upstream_info.msg})
  end

  kong.service.set_target(upstream_info.data.host, upstream_info.data.port)
  ngx.log(ngx.ERR, ngx.var.upstream_uri)

  -- -- In this simple form, there is no manual connection step, so the body is read
  -- -- all in one go, including any trailers, and the connection closed or keptalive
  -- -- for you.

  -- ngx.status = res.status

  -- for k,v in pairs(res.headers) do
  --     --
  -- end

  -- ngx.say(res.body)

  -- Implement any custom logic here
end

function CustomHandler:header_filter(config)
  -- Eventually, execute the parent implementation
  -- (will log that your plugin is entering this context)
  CustomHandler.super.header_filter(self)

  -- Implement any custom logic here
end

-- function CustomHandler:body_filter(config)
--   -- Eventually, execute the parent implementation
--   -- (will log that your plugin is entering this context)
--   CustomHandler.super.body_filter(self)

--   -- Implement any custom logic here
-- end

function CustomHandler:log(config)
  -- Eventually, execute the parent implementation
  -- (will log that your plugin is entering this context)
  CustomHandler.super.log(self)

  -- Implement any custom logic here
end

-- This module needs to return the created table, so that Kong
-- can execute those functions.
return CustomHandler