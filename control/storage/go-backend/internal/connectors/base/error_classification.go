package base

import (
	"context"
	"errors"
	"net"
	"net/http"
	"strings"
)

type ErrorClass string

const (
	ErrorClassUnknown     ErrorClass = "unknown"
	ErrorClassTimeout     ErrorClass = "timeout"
	ErrorClassNetwork     ErrorClass = "network"
	ErrorClassCanceled    ErrorClass = "canceled"
	ErrorClassAuth        ErrorClass = "auth"
	ErrorClassQuota       ErrorClass = "quota"
	ErrorClassBadRequest  ErrorClass = "bad_request"
	ErrorClassNotFound    ErrorClass = "not_found"
	ErrorClassUpstream5xx ErrorClass = "upstream_5xx"
	ErrorClassSchemaDrift ErrorClass = "schema_drift"
)

func ClassifyHTTPStatus(statusCode int) ErrorClass {
	switch statusCode {
	case http.StatusUnauthorized, http.StatusForbidden:
		return ErrorClassAuth
	case http.StatusTooManyRequests:
		return ErrorClassQuota
	case http.StatusNotFound:
		return ErrorClassNotFound
	case http.StatusBadRequest, http.StatusUnprocessableEntity:
		return ErrorClassBadRequest
	}
	if statusCode >= 500 {
		return ErrorClassUpstream5xx
	}
	return ErrorClassUnknown
}

func IsRetryableClass(class ErrorClass) bool {
	switch class {
	case ErrorClassTimeout, ErrorClassNetwork, ErrorClassQuota, ErrorClassUpstream5xx:
		return true
	default:
		return false
	}
}

func ClassifyError(err error, resp *http.Response) ErrorClass {
	if resp != nil {
		if cls := ClassifyHTTPStatus(resp.StatusCode); cls != ErrorClassUnknown {
			return cls
		}
	}

	if err == nil {
		return ErrorClassUnknown
	}

	if errors.Is(err, context.Canceled) {
		return ErrorClassCanceled
	}
	if errors.Is(err, context.DeadlineExceeded) {
		return ErrorClassTimeout
	}

	var netErr net.Error
	if errors.As(err, &netErr) {
		if netErr.Timeout() {
			return ErrorClassTimeout
		}
		return ErrorClassNetwork
	}

	var reqErr *RequestError
	if errors.As(err, &reqErr) {
		if cls := ClassifyHTTPStatus(reqErr.StatusCode); cls != ErrorClassUnknown {
			return cls
		}
		body := strings.ToLower(strings.TrimSpace(reqErr.Body))
		msg := strings.ToLower(strings.TrimSpace(reqErr.Message))
		if strings.Contains(body, "schema") || strings.Contains(msg, "schema") ||
			strings.Contains(body, "unexpected field") || strings.Contains(msg, "unexpected field") {
			return ErrorClassSchemaDrift
		}
	}

	msg := strings.ToLower(strings.TrimSpace(err.Error()))
	switch {
	case strings.Contains(msg, "timeout"):
		return ErrorClassTimeout
	case strings.Contains(msg, "connection reset"), strings.Contains(msg, "connection refused"), strings.Contains(msg, "eof"):
		return ErrorClassNetwork
	case strings.Contains(msg, "429"), strings.Contains(msg, "rate limit"), strings.Contains(msg, "quota"):
		return ErrorClassQuota
	case strings.Contains(msg, "unauthorized"), strings.Contains(msg, "forbidden"), strings.Contains(msg, "invalid api key"):
		return ErrorClassAuth
	case strings.Contains(msg, "schema"), strings.Contains(msg, "unexpected field"), strings.Contains(msg, "decode"):
		return ErrorClassSchemaDrift
	default:
		return ErrorClassUnknown
	}
}
