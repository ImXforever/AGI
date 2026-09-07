-- counter_window.lua
-- Sliding-window rate limiter using a sorted set.
-- KEYS[1] = rate limit key (e.g. rl:telegram:user:12345)
-- ARGV[1] = window size in seconds
-- ARGV[2] = max requests allowed in window
-- ARGV[3] = current unix timestamp (microseconds or seconds with fraction)
-- ARGV[4] = unique request identifier (e.g. uuid or timestamp+random)
--
-- Returns {allowed (1/0), remaining, retry_after_seconds}

local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local request_id = ARGV[4]

local window_start = now - window

-- Remove expired entries
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

-- Count current entries
local count = redis.call('ZCARD', key)

if count >= limit then
    -- Get the oldest entry to calculate retry-after
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 0
    if #oldest >= 2 then
        retry_after = math.ceil(tonumber(oldest[2]) + window - now)
        if retry_after < 0 then
            retry_after = 0
        end
    end
    return {0, 0, retry_after}
end

-- Add the new request
redis.call('ZADD', key, now, request_id)
redis.call('EXPIRE', key, window)

local remaining = limit - count - 1
return {1, remaining, 0}
