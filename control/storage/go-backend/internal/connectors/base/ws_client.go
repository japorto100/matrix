package base

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// WebsocketConfig defines the configuration for the base websocket client.
type WebsocketConfig struct {
	URL                 string
	HandshakeTimeout    time.Duration
	PingInterval        time.Duration
	WriteWait           time.Duration
	MaxMessageSize      int64
	ReconnectInterval   time.Duration
	MaxReconnectRetries int
}

// WebsocketClient provides a generic, robust wrapper around gorilla/websocket.
// It features automatic reconnections, ping/pong keep-alives, and safe concurrent writes.
type WebsocketClient struct {
	config WebsocketConfig

	conn *websocket.Conn
	mu   sync.Mutex // Protects conn and connection state

	dialer *websocket.Dialer

	isConnected bool
	ctx         context.Context
	cancel      context.CancelFunc

	// messageHandler is called for every incoming message.
	messageHandler func(messageType int, message []byte)
	// errorHandler is called when a non-recoverable error occurs or a reconnect fails.
	errorHandler func(err error)
	// onConnect is called immediately after a successful connection (useful for sending subscriptions).
	onConnect func() error
}

func NewWebsocketClient(config WebsocketConfig) *WebsocketClient {
	if config.HandshakeTimeout <= 0 {
		config.HandshakeTimeout = 5 * time.Second
	}
	if config.PingInterval <= 0 {
		config.PingInterval = 30 * time.Second
	}
	if config.WriteWait <= 0 {
		config.WriteWait = 10 * time.Second
	}
	if config.ReconnectInterval <= 0 {
		config.ReconnectInterval = 2 * time.Second
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &WebsocketClient{
		config: config,
		dialer: &websocket.Dialer{
			HandshakeTimeout: config.HandshakeTimeout,
		},
		ctx:    ctx,
		cancel: cancel,
	}
}

// SetMessageHandler sets the callback for incoming messages.
func (c *WebsocketClient) SetMessageHandler(handler func(messageType int, message []byte)) {
	c.messageHandler = handler
}

// SetErrorHandler sets the callback for errors.
func (c *WebsocketClient) SetErrorHandler(handler func(err error)) {
	c.errorHandler = handler
}

// SetOnConnect sets the callback executed immediately after a successful connection.
// If this callback returns an error, the connection is closed and a reconnect is triggered.
func (c *WebsocketClient) SetOnConnect(handler func() error) {
	c.onConnect = handler
}

// Connect establishes the websocket connection and starts the read/ping loops.
func (c *WebsocketClient) Connect(ctx context.Context) error {
	c.mu.Lock()
	if c.isConnected {
		c.mu.Unlock()
		return nil
	}
	c.mu.Unlock()

	return c.connectInternal(ctx, 0)
}

func (c *WebsocketClient) connectInternal(ctx context.Context, retryCount int) error {
	c.mu.Lock()
	conn, resp, err := c.dialer.DialContext(ctx, c.config.URL, nil)
	if err != nil {
		c.mu.Unlock()
		status := 0
		if resp != nil {
			status = resp.StatusCode
		}
		if retryCount < c.config.MaxReconnectRetries || c.config.MaxReconnectRetries == 0 {
			time.Sleep(c.config.ReconnectInterval)
			return c.connectInternal(ctx, retryCount+1)
		}
		return fmt.Errorf("websocket dial failed after %d retries: %w (status: %d)", retryCount, err, status)
	}

	c.conn = conn
	c.isConnected = true
	if c.config.MaxMessageSize > 0 {
		c.conn.SetReadLimit(c.config.MaxMessageSize)
	}

	// Setup ping/pong handlers
	c.conn.SetPongHandler(func(string) error {
		_ = c.conn.SetReadDeadline(time.Now().Add(c.config.PingInterval + c.config.WriteWait))
		return nil
	})
	_ = c.conn.SetReadDeadline(time.Now().Add(c.config.PingInterval + c.config.WriteWait))

	c.mu.Unlock()

	// Execute OnConnect callback (e.g. for subscriptions)
	if c.onConnect != nil {
		if err := c.onConnect(); err != nil {
			c.Close()
			return fmt.Errorf("onConnect callback failed: %w", err)
		}
	}

	go c.readLoop()
	go c.pingLoop()

	return nil
}

// WriteJSON sends a JSON encoded message to the websocket concurrently safe.
func (c *WebsocketClient) WriteJSON(v any) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.isConnected || c.conn == nil {
		return fmt.Errorf("websocket is not connected")
	}

	_ = c.conn.SetWriteDeadline(time.Now().Add(c.config.WriteWait))
	if err := c.conn.WriteJSON(v); err != nil {
		return fmt.Errorf("write websocket json message: %w", err)
	}
	return nil
}

// WriteMessage sends a raw message to the websocket concurrently safe.
func (c *WebsocketClient) WriteMessage(messageType int, data []byte) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.isConnected || c.conn == nil {
		return fmt.Errorf("websocket is not connected")
	}

	_ = c.conn.SetWriteDeadline(time.Now().Add(c.config.WriteWait))
	if err := c.conn.WriteMessage(messageType, data); err != nil {
		return fmt.Errorf("write websocket message type %d: %w", messageType, err)
	}
	return nil
}

// Close gracefully closes the websocket connection.
func (c *WebsocketClient) Close() {
	c.cancel() // Stop the loops

	c.mu.Lock()
	defer c.mu.Unlock()

	if c.isConnected && c.conn != nil {
		// Send close message
		_ = c.conn.SetWriteDeadline(time.Now().Add(c.config.WriteWait))
		_ = c.conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
		_ = c.conn.Close()
		c.isConnected = false
	}
}

// reconnect attempts to re-establish the connection.
func (c *WebsocketClient) reconnect() {
	c.mu.Lock()
	if !c.isConnected {
		c.mu.Unlock()
		return // Already disconnected intentionally
	}
	// Clean up old connection
	if c.conn != nil {
		_ = c.conn.Close()
	}
	c.isConnected = false
	c.mu.Unlock()

	// Attempt reconnect
	if err := c.connectInternal(c.ctx, 0); err != nil {
		if c.errorHandler != nil {
			c.errorHandler(fmt.Errorf("websocket reconnect failed: %w", err))
		}
	}
}

func (c *WebsocketClient) readLoop() {
	for {
		select {
		case <-c.ctx.Done():
			return
		default:
		}

		c.mu.Lock()
		conn := c.conn
		isConnected := c.isConnected
		c.mu.Unlock()

		if !isConnected || conn == nil {
			return
		}

		messageType, message, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
				// Unexpected close, initiate reconnect
				go c.reconnect()
				return
			}
			// Normal close, exit loop
			return
		}

		if c.messageHandler != nil {
			c.messageHandler(messageType, message)
		}
	}
}

func (c *WebsocketClient) pingLoop() {
	ticker := time.NewTicker(c.config.PingInterval)
	defer ticker.Stop()

	for {
		select {
		case <-c.ctx.Done():
			return
		case <-ticker.C:
			c.mu.Lock()
			conn := c.conn
			isConnected := c.isConnected
			c.mu.Unlock()

			if !isConnected || conn == nil {
				return
			}

			_ = conn.SetWriteDeadline(time.Now().Add(c.config.WriteWait))
			if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				// Ping failed, likely disconnected
				go c.reconnect()
				return
			}
		}
	}
}
