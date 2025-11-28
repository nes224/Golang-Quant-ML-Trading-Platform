
include app.env
DB_URL=${DB_SOURCE}

postgres:
	docker run --name postgres14 -p 5434:5432 -e POSTGRES_USER=root -e POSTGRES_PASSWORD=secret -d postgres:14-alpine
createdb:
	docker exec -it postgres14 createdb --username=postgres --owner=postgres abs_db

dropdb:
	docker exec -it postgres14 dropdb abs_db

migrateup:
	migrate -path golang_backend/internal/migration -database "$(DB_URL)" -verbose up

migrateup1:
	migrate -path golang_backend/internal/migration -database "$(DB_URL)" -verbose up 1

migratedown:
	migrate -path golang_backend/internal/migration -database "$(DB_URL)" -verbose down

migratedown1:
	migrate -path golang_backend/internal/migration -database "$(DB_URL)" -verbose down 1

new_migration:
	migrate create -ext sql -dir golang_backend/internal/migration -seq $(name)

db_docs:
	dbdocs build doc/db.dbml

db_schema:
	dbml2sql --postgres -o doc/schema.sql doc/db.dbml

sqlc:
	sqlc generate

test:
	go test -v -cover -short ./...

server:
	air

mock:
	mockgen -source=golang_backend/internal/sqlc/store.go -aux_files=github.com/abs/go_billing/internal/sqlc=internal/sqlc/querier.go -package mockdb -destination internal/mock/store.go

proto:
	rm -f pb/*.go
	rm -f doc/swagger/*.swagger.json
	protoc --proto_path=proto --go_out=pb --go_opt=paths=source_relative \
	--go-grpc_out=pb --go-grpc_opt=paths=source_relative \
	--grpc-gateway_out=pb --grpc-gateway_opt=paths=source_relative \
	--openapiv2_out=doc/swagger --openapiv2_opt=allow_merge=true,merge_file_name=abs_db \
    proto/*.proto
	statik -src=./doc/swagger -dest=./doc

evans:
	evans --host localhost --port 9090 -r repl

redis:
	docker run --name redis -p 6379:6379 -d redis:7-alpine

.PHONY: postgres createdb dropdb migrateup migratedown migrateup1 migratedown1 new_migration db_docs db_schema sqlc test server mock proto evans redis
