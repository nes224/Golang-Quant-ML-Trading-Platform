FROM golang:1.24-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
RUN apk add --update --no-cache bash git openssh
RUN go install github.com/air-verse/air@v1.52.3
COPY . .
RUN go build -o main . 

EXPOSE 5001
CMD ["air","./app/main.go","-b","0.0.0.0"]