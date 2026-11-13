# ai-generated: 100% - Codex wrote positive and negative cases for the svcdesk review rules.
def parsing_bad(value):
    # ruleid: svcdesk-bare-except
    try:
        return int(value)
    except:
        return None


def parsing_good(value):
    # ok: svcdesk-bare-except
    try:
        return int(value)
    except ValueError:
        return None


async def request_bad(client):
    # ruleid: svcdesk-broad-async-except
    try:
        return await client.get('/health')
    except Exception:
        return None


async def request_good(client):
    # ok: svcdesk-broad-async-except
    try:
        return await client.get('/health')
    except TimeoutError:
        return None


def synchronous_boundary(callback):
    # ok: svcdesk-broad-async-except
    try:
        return callback()
    except Exception:
        return None
