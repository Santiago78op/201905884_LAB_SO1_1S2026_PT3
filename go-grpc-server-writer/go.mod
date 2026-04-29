module 201905884_LAB_SO1_1S2026_PT3/go-grpc-server-writer

go 1.26.2

require (
	github.com/rabbitmq/amqp091-go v1.10.0
	google.golang.org/grpc v1.80.0
)

require (
	golang.org/x/net v0.49.0 // indirect
	golang.org/x/sys v0.40.0 // indirect
	golang.org/x/text v0.33.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20260120221211-b8f7ae30c516 // indirect
	google.golang.org/protobuf v1.36.11 // indirect
)

// Import 201905884_LAB_SO1_1S2026_PT3/proto
require 201905884_LAB_SO1_1S2026_PT3/proto v0.0.0-20260417180000-000000000000

// Replace 201905884_LAB_SO1_1S2026_PT3/proto with the actual path to the proto package
replace 201905884_LAB_SO1_1S2026_PT3/proto => ../proto
