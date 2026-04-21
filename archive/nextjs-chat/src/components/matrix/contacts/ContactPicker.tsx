"use client";

import { Search } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useEffect, useRef, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { type Contact, useContacts } from "@/lib/matrix/hooks/useContacts";

interface Props {
	client: MatrixClient;
	/** Callback wenn ein Kontakt ausgewaehlt wird */
	onSelect: (userId: string) => void;
	/** Placeholder-Text */
	placeholder?: string;
	/** Aktueller Wert (kontrolliert) */
	value?: string;
	/** Wertaenderung */
	onChange?: (value: string) => void;
	/** Autofocus */
	autoFocus?: boolean;
}

export function ContactPicker({
	client,
	onSelect,
	placeholder = "Name oder @user:server",
	value: controlledValue,
	onChange: controlledOnChange,
	autoFocus,
}: Props) {
	const { dmContacts, searchUsers } = useContacts(client);
	const [internalValue, setInternalValue] = useState("");
	const [searchResults, setSearchResults] = useState<Contact[]>([]);
	const [isSearching, setIsSearching] = useState(false);
	const [showDropdown, setShowDropdown] = useState(false);
	const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);
	const containerRef = useRef<HTMLDivElement>(null);

	const value = controlledValue ?? internalValue;
	const setValue = (v: string) => {
		if (controlledOnChange) controlledOnChange(v);
		else setInternalValue(v);
	};

	// Suche mit Debounce
	useEffect(() => {
		if (!value.trim()) {
			setSearchResults([]);
			return;
		}
		if (debounceRef.current) clearTimeout(debounceRef.current);
		debounceRef.current = setTimeout(async () => {
			setIsSearching(true);
			const results = await searchUsers(value);
			setSearchResults(results);
			setIsSearching(false);
		}, 300);
		return () => {
			if (debounceRef.current) clearTimeout(debounceRef.current);
		};
	}, [value, searchUsers]);

	// Click-Outside schliessen
	useEffect(() => {
		function handleClick(e: MouseEvent) {
			if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
				setShowDropdown(false);
			}
		}
		document.addEventListener("mousedown", handleClick);
		return () => document.removeEventListener("mousedown", handleClick);
	}, []);

	// Gefilterte DM-Kontakte (nach Eingabe)
	const filteredDmContacts = value.trim()
		? dmContacts.filter(
				(c) =>
					c.displayName.toLowerCase().includes(value.toLowerCase()) ||
					c.userId.toLowerCase().includes(value.toLowerCase()),
			)
		: dmContacts;

	const handleSelect = (contact: Contact) => {
		setValue(contact.userId);
		onSelect(contact.userId);
		setShowDropdown(false);
	};

	return (
		<div ref={containerRef} className="relative">
			<div className="relative">
				<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
				<Input
					value={value}
					onChange={(e) => {
						setValue(e.target.value);
						setShowDropdown(true);
					}}
					onFocus={() => setShowDropdown(true)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && value.trim().startsWith("@")) {
							onSelect(value.trim());
							setShowDropdown(false);
						}
					}}
					placeholder={placeholder}
					className="pl-8"
					autoFocus={autoFocus}
				/>
			</div>

			{/* Dropdown */}
			{showDropdown &&
				(filteredDmContacts.length > 0 || searchResults.length > 0 || isSearching) && (
					<div className="absolute top-full left-0 right-0 mt-1 z-50 bg-popover border border-border rounded-lg shadow-lg max-h-[240px] overflow-y-auto">
						{/* DM Kontakte */}
						{filteredDmContacts.length > 0 && (
							<>
								<p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-3 py-1.5">
									Kontakte
								</p>
								{filteredDmContacts.slice(0, 5).map((contact) => (
									<ContactRow key={contact.userId} contact={contact} onSelect={handleSelect} />
								))}
							</>
						)}

						{/* Server-Suche */}
						{searchResults.length > 0 && (
							<>
								{filteredDmContacts.length > 0 && <div className="h-px bg-border mx-2" />}
								<p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider px-3 py-1.5">
									Verzeichnis
								</p>
								{searchResults.slice(0, 5).map((contact) => (
									<ContactRow key={contact.userId} contact={contact} onSelect={handleSelect} />
								))}
							</>
						)}

						{isSearching && (
							<p className="text-xs text-muted-foreground text-center py-2">Suche...</p>
						)}
					</div>
				)}
		</div>
	);
}

function ContactRow({
	contact,
	onSelect,
}: {
	contact: Contact;
	onSelect: (contact: Contact) => void;
}) {
	const initials = contact.displayName.slice(0, 2).toUpperCase() || "?";
	return (
		<button
			type="button"
			className="w-full flex items-center gap-2.5 px-3 py-1.5 hover:bg-accent/50 transition-colors text-left"
			onClick={() => onSelect(contact)}
		>
			<div className="relative shrink-0">
				<Avatar className="h-7 w-7">
					{contact.avatarUrl && <AvatarImage src={contact.avatarUrl} alt={contact.displayName} />}
					<AvatarFallback className="text-[10px] font-semibold bg-muted text-muted-foreground">
						{initials}
					</AvatarFallback>
				</Avatar>
				{contact.isOnline && (
					<span className="absolute bottom-0 right-0 h-2 w-2 rounded-full bg-emerald-500 ring-1 ring-background" />
				)}
			</div>
			<div className="flex-1 min-w-0">
				<p className="text-sm font-medium truncate">{contact.displayName}</p>
				<p className="text-[10px] text-muted-foreground truncate">{contact.userId}</p>
			</div>
			{contact.isDmContact && (
				<span className="text-[9px] text-muted-foreground/60 shrink-0">DM</span>
			)}
		</button>
	);
}
