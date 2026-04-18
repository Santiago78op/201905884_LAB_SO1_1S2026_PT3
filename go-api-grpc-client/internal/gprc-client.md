# gRPC Client
En ``internal/client/grpc-client.go``, necesitas un struct con:

- Una conexión ``gRPC (*grpc.ClientConn)``
- Un cliente del servicio ``proto (proto.WarReportServiceClient)``  