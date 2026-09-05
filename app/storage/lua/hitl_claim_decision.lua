-- hitl_claim_decision.lua
-- Atomically apply a human decision to a HITL approval item.
-- KEYS[1] = hitl:meta:{approval_id}
-- KEYS[2] = hitl:decided:{approval_id}
-- ARGV[1] = expected status ("pending")
-- ARGV[2] = new status (approved/rejected/edited)
-- ARGV[3] = actor (operator id or username)
-- ARGV[4] = current unix timestamp (seconds)
-- ARGV[5] = optional edited payload JSON (empty string if not edited)
-- ARGV[6] = optional note text (empty string if none)
--
-- Returns 1 if successfully applied, 0 if already decided.

local meta_key = KEYS[1]
local decided_key = KEYS[2]
local expected = ARGV[1]
local new_status = ARGV[2]
local actor = ARGV[3]
local now = ARGV[4]
local edited_payload = ARGV[5]
local note = ARGV[6]

local current = redis.call('HGET', meta_key, 'status')
if current ~= expected then
    return 0
end

redis.call('HSET', meta_key,
    'status', new_status,
    'actor', actor,
    'decided_at', now
)

if edited_payload and edited_payload ~= '' then
    redis.call('HSET', meta_key, 'edited_payload', edited_payload)
end

if note and note ~= '' then
    redis.call('HSET', meta_key, 'note', note)
end

redis.call('SET', decided_key, new_status, 'EX', 86400)

return 1
