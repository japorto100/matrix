"use client";

// DW11 tab wrapper — uploads tab

import { useQueryClient } from "@tanstack/react-query";
import { UploadDropzone } from "./UploadDropzone";

export function FilesUploadsTab() {
	const queryClient = useQueryClient();

	return (
		<div className="flex flex-col gap-4 p-4 max-w-xl">
			<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
				Upload Files
			</p>
			<UploadDropzone
				onUploaded={() => {
					// invalidate overview + file list after successful upload
					void queryClient.invalidateQueries({ queryKey: ["files-overview"] });
					void queryClient.invalidateQueries({ queryKey: ["files-list"] });
				}}
			/>
		</div>
	);
}
