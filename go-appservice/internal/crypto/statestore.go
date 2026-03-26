// Package crypto kapselt E2EE-Logik via mautrix-go OlmMachine.
// Go Appservice übernimmt Crypto — Python Bridge bekommt Klartext (Option C).
package crypto

import (
	"context"
	"errors"
	"fmt"
	"sync"

	"maunium.net/go/mautrix"
	"maunium.net/go/mautrix/event"
	"maunium.net/go/mautrix/id"
)

// StateStore implementiert crypto.StateStore für OlmMachine.
// Cached Verschlüsselungsstatus und Raum-Mitglieder im Speicher,
// fragt den Homeserver bei Cache-Miss.
type StateStore struct {
	client *mautrix.Client

	mu        sync.RWMutex
	encrypted map[id.RoomID]bool
	members   map[id.RoomID]map[id.UserID]bool
}

// NewStateStore erstellt einen neuen StateStore.
func NewStateStore(client *mautrix.Client) *StateStore {
	return &StateStore{
		client:    client,
		encrypted: make(map[id.RoomID]bool),
		members:   make(map[id.RoomID]map[id.UserID]bool),
	}
}

// IsEncrypted prüft ob ein Raum E2EE aktiviert hat.
// Cached das Ergebnis nach der ersten Abfrage.
func (s *StateStore) IsEncrypted(ctx context.Context, roomID id.RoomID) (bool, error) {
	s.mu.RLock()
	if v, ok := s.encrypted[roomID]; ok {
		s.mu.RUnlock()
		return v, nil
	}
	s.mu.RUnlock()

	var content event.EncryptionEventContent
	err := s.client.StateEvent(ctx, roomID, event.StateEncryption, "", &content)

	encrypted := true
	if err != nil {
		var httpErr mautrix.HTTPError
		if errors.As(err, &httpErr) && httpErr.Response != nil && httpErr.Response.StatusCode == 404 {
			encrypted = false
		} else {
			return false, fmt.Errorf("get encryption state (room=%s): %w", roomID, err)
		}
	}

	s.mu.Lock()
	s.encrypted[roomID] = encrypted
	s.mu.Unlock()

	return encrypted, nil
}

// GetEncryptionEvent gibt den m.room.encryption State-Event zurück.
func (s *StateStore) GetEncryptionEvent(ctx context.Context, roomID id.RoomID) (*event.EncryptionEventContent, error) {
	var content event.EncryptionEventContent
	if err := s.client.StateEvent(ctx, roomID, event.StateEncryption, "", &content); err != nil {
		return nil, fmt.Errorf("get encryption event (room=%s): %w", roomID, err)
	}
	return &content, nil
}

// FindSharedRooms gibt alle Räume zurück in denen Bot und userID beide Mitglied sind.
func (s *StateStore) FindSharedRooms(_ context.Context, userID id.UserID) ([]id.RoomID, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var rooms []id.RoomID
	for roomID, members := range s.members {
		if members[userID] {
			rooms = append(rooms, roomID)
		}
	}
	return rooms, nil
}

// SetEncrypted aktualisiert den Cache-Eintrag für einen Raum.
func (s *StateStore) SetEncrypted(roomID id.RoomID, encrypted bool) {
	s.mu.Lock()
	s.encrypted[roomID] = encrypted
	s.mu.Unlock()
}

// AddMember trägt einen User als Mitglied eines Raums ein.
func (s *StateStore) AddMember(roomID id.RoomID, userID id.UserID) {
	s.mu.Lock()
	if _, ok := s.members[roomID]; !ok {
		s.members[roomID] = make(map[id.UserID]bool)
	}
	s.members[roomID][userID] = true
	s.mu.Unlock()
}

// GetMembers gibt alle gecachten Mitglieder eines Raums zurück.
func (s *StateStore) GetMembers(roomID id.RoomID) []id.UserID {
	s.mu.RLock()
	defer s.mu.RUnlock()
	members := s.members[roomID]
	if len(members) == 0 {
		return nil
	}
	result := make([]id.UserID, 0, len(members))
	for uid := range members {
		result = append(result, uid)
	}
	return result
}

// RemoveMember entfernt einen User aus dem Mitglieder-Cache.
func (s *StateStore) RemoveMember(roomID id.RoomID, userID id.UserID) {
	s.mu.Lock()
	if members, ok := s.members[roomID]; ok {
		delete(members, userID)
	}
	s.mu.Unlock()
}
