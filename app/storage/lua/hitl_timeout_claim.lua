-- hitl_timeout_claim.lua
-- Atomically claim a HITL item that has timed out.
-- KEYS[1] = hitl:meta:{approval_id}
-- ARGV[1] = expected status ("pending")
-- ARGV[2] = new status ("timeout")
-- ARGV[3] = current unix timestamp (seconds)
--
-- Returns 1 if successfully claimed, 0 otherwise.

local key = KEYS[1]
local expected = ARGV[1]
local new_status = ARGV[2]
local now = ARGV[3]

local current = redis.call('HGET', key, 'status')
if current ~= expected then
    return 0
end

redis.call('HSET', key, 'status', new_status, 'decided_at', now)
return 1
