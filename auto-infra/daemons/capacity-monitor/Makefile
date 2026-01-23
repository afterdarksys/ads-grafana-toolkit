.PHONY: build clean install deploy test

BINARY_NAME=capacity-monitor
INSTALL_PATH=/usr/local/bin
SYSTEMD_PATH=/etc/systemd/system

build:
	go build -o $(BINARY_NAME) -ldflags="-s -w" .

build-linux:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o $(BINARY_NAME)-linux-amd64 -ldflags="-s -w" .
	CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o $(BINARY_NAME)-linux-arm64 -ldflags="-s -w" .

clean:
	rm -f $(BINARY_NAME) $(BINARY_NAME)-linux-*

install: build
	sudo cp $(BINARY_NAME) $(INSTALL_PATH)/
	sudo chmod +x $(INSTALL_PATH)/$(BINARY_NAME)

deploy: build-linux
	@echo "Build binaries created. Deploy to instances manually or via script."

test:
	go test -v ./...

run:
	./$(BINARY_NAME)
