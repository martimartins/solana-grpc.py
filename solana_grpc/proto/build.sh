python -m grpc_tools.protoc -I. --python_out=../generated --grpc_python_out=../generated --pyi_out=../generated geyser.proto
python -m grpc_tools.protoc -I. --python_out=../generated --grpc_python_out=../generated --pyi_out=../generated solana-storage.proto

