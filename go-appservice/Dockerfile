# Go Appservice — Multi-Stage Build
FROM golang:1.26-alpine AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /appservice ./cmd/appservice

FROM alpine:3.21
RUN apk add --no-cache ca-certificates tzdata wget
COPY --from=builder /appservice /usr/local/bin/appservice

EXPOSE 8090
ENTRYPOINT ["appservice"]
