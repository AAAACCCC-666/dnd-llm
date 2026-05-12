"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";

interface DocumentQueryProps {
  onOpenDocument?: () => void;
}

export function DocumentQuery({ onOpenDocument }: DocumentQueryProps) {
  const handleOpenDocument = () => {
    // Open PDF file - file is now in public directory
    const pdfPath = "/5eDnD_玩家手册PHB_中译v1.6版.pdf";
    window.open(pdfPath, "_blank");

    // If there is a custom callback function, also execute it
    if (onOpenDocument) {
      onOpenDocument();
    }
  };

  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">
            Document Query
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleOpenDocument}
            className="flex items-center gap-2"
          >
            <FileText className="h-4 w-4" />
            Open Player's Handbook
          </Button>
        </div>
      </div>
    </div>
  );
}