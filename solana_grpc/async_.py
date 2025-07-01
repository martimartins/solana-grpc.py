import asyncio
from typing import AsyncGenerator
import grpc
from grpc.aio import ClientCallDetails, AioRpcError

from solana_grpc.generated import geyser_pb2
from solana_grpc.generated import geyser_pb2_grpc


class _WithHeaders:
    def __init__(self, *headers: tuple[str, str]):
        self.headers = headers

    def _insert_headers(self, new_metadata, client_call_details) -> ClientCallDetails:
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        metadata.extend(new_metadata)

        return ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )


class WithHeadersStreamStream(_WithHeaders, grpc.aio.StreamStreamClientInterceptor):
    async def intercept_stream_stream(
        self, continuation, client_call_details, request_iterator
    ):
        new_client_call_details = self._insert_headers(
            self.headers, client_call_details
        )
        return await continuation(new_client_call_details, request_iterator)  # type: ignore


class WithHeadersUnaryUnary(_WithHeaders, grpc.aio.UnaryUnaryClientInterceptor):
    async def intercept_unary_unary(self, continuation, client_call_details, request):
        new_client_call_details = self._insert_headers(
            self.headers, client_call_details
        )
        return await continuation(new_client_call_details, request)


class GeyserClient:
    def __init__(self, target: str, x_token: str):
        self.stub: geyser_pb2_grpc.GeyserStub
        self.channel: grpc.aio.Channel
        self._target = target
        self._x_token = x_token

    async def start(self):
        interceptors = [
            WithHeadersStreamStream(("x-token", self._x_token)),
            WithHeadersUnaryUnary(("x-token", self._x_token)),
        ]
        self.channel = grpc.aio.secure_channel(
            self._target,
            grpc.ssl_channel_credentials(),
            interceptors=interceptors,
        )
        self.stub = geyser_pb2_grpc.GeyserStub(self.channel)

    async def close(self):
        await self.channel.close()
        self.channel = None  # type: ignore
        self.stub = None  # type: ignore

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def ping(self, count):
        request = geyser_pb2.PingRequest(count=count)
        return await self.stub.Ping(request)

    async def get_version(self):
        request = geyser_pb2.GetVersionRequest()
        return await self.stub.GetVersion(request)

    async def get_latest_blockhash(self, commitment=None):
        request = geyser_pb2.GetLatestBlockhashRequest(commitment=commitment)
        return await self.stub.GetLatestBlockhash(request)

    async def get_block_height(self, commitment=None):
        request = geyser_pb2.GetBlockHeightRequest(commitment=commitment)
        return await self.stub.GetBlockHeight(request)

    async def subscribe(
        self, *requests: geyser_pb2.SubscribeRequest
    ) -> AsyncGenerator[geyser_pb2.SubscribeUpdate, None]:
        async for response in self.stub.Subscribe(iter(requests)):
            yield response


async def main():
    async with GeyserClient("...", "...") as client:
        ver = await client.get_version()
        print(f"{ver=}")

        PUMP_FUN_FILTER = geyser_pb2.SubscribeRequestFilterTransactions(
            account_include=["TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"],
            account_exclude=[],
            account_required=[],
        )
        req = geyser_pb2.SubscribeRequest(
            slots={},
            accounts={},
            blocks={},
            transactions={"pumpfun": PUMP_FUN_FILTER},
            blocks_meta={},
            accounts_data_slice={},
            entry={},
            commitment=geyser_pb2.CommitmentLevel.PROCESSED,
        )

        try:
            async for data in client.subscribe(req):
                print(data)
        except AioRpcError as e:
            print(f"Subscription terminated with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
