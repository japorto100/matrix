package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/pem"
	"fmt"
	"os"
)

func main() {
	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		panic(err)
	}

	// gomatrixserverlib erwartet PEM Type "MATRIX PRIVATE KEY"
	// mit rohen 64-byte ed25519 Private-Key Bytes (seed+public)
	block := &pem.Block{
		Type: "MATRIX PRIVATE KEY",
		Headers: map[string]string{
			"Key-ID": "ed25519:auto",
		},
		Bytes: priv, // 64 bytes: seed (32) + public key (32)
	}

	f, err := os.Create("D:/matrix/homeserver/dendrite_key.pem")
	if err != nil {
		panic(err)
	}
	defer f.Close()
	pem.Encode(f, block)
	fmt.Println("Key generiert (64 bytes ED25519)")
}
