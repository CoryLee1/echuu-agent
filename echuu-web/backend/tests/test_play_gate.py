import asyncio

from state import GlobalStateManager


def test_play_gate_blocks_until_requested():
    async def run():
        manager = GlobalStateManager()
        manager.reset_play_gate()
        assert manager.play_requested() is False
        waiter = asyncio.create_task(manager.wait_for_play())
        await asyncio.sleep(0)
        assert waiter.done() is False
        manager.request_play()
        await waiter
        assert manager.play_requested() is True

    asyncio.run(run())


def test_stop_can_release_play_gate():
    async def run():
        manager = GlobalStateManager()
        manager.reset_play_gate()
        waiter = asyncio.create_task(manager.wait_for_play())
        await asyncio.sleep(0)
        manager.request_play()
        await waiter

    asyncio.run(run())
