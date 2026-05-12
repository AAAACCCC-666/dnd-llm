"use client";

import * as React from "react";
import { useState, useEffect, useCallback } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, Package, Sword, Shield, FlaskConical, ScrollText, Coins, RefreshCw } from "lucide-react";
import { buildApiUrl } from "@/lib/api";

interface InventoryItem {
  name: string;
  quantity: number;
  type: string;
  description?: string;
  weight?: number;
}

interface CharacterData {
  id: string;
  name: string;
  equipment: Record<string, number>;
  inventory_items: Record<string, number>;
  gold?: number;
}

interface InventoryProps {
  sessionId: string;
  refreshToken?: number;
}

const getItemType = (itemName: string): string => {
  const lowerName = itemName.toLowerCase();

  if (lowerName.includes('sword') || lowerName.includes('axe') || lowerName.includes('bow') ||
    lowerName.includes('dagger') || lowerName.includes('spear') || lowerName.includes('mace')) {
    return "weapon";
  }
  if (lowerName.includes('armor') || lowerName.includes('shield') || lowerName.includes('helmet') ||
    lowerName.includes('plate') || lowerName.includes('mail')) {
    return "armor";
  }
  if (lowerName.includes('potion') || lowerName.includes('elixir') || lowerName.includes('healing')) {
    return "potion";
  }
  if (lowerName.includes('scroll') || lowerName.includes('spell') || lowerName.includes('tome')) {
    return "scroll";
  }
  if (lowerName.includes('gold') || lowerName.includes('coin') || lowerName.includes('silver')) {
    return "currency";
  }
  if (lowerName.includes('key') || lowerName.includes('torch') || lowerName.includes('rope') ||
    lowerName.includes('lantern') || lowerName.includes('tool')) {
    return "tool";
  }

  return "misc";
};

const getItemDescription = (itemName: string): string => {
  const type = getItemType(itemName);
  switch (type) {
    case "weapon":
      return "A weapon for combat";
    case "armor":
      return "Protective gear";
    case "potion":
      return "A magical or alchemical concoction";
    case "scroll":
      return "A magical scroll";
    case "currency":
      return "Currency for trading";
    case "tool":
      return "A useful tool or item";
    default:
      return "A miscellaneous item";
  }
};

const getItemWeight = (itemName: string): number => {
  const type = getItemType(itemName);
  switch (type) {
    case "weapon":
      return 2.5;
    case "armor":
      return 8.0;
    case "potion":
      return 0.5;
    case "scroll":
      return 0.1;
    case "currency":
      return 0.02;
    case "tool":
      return 1.0;
    default:
      return 0.5;
  }
};

export function Inventory({ sessionId, refreshToken }: InventoryProps) {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [gold, setGold] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadInventory = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(buildApiUrl(`/characters/session/${sessionId}`));
      if (!response.ok) {
        throw new Error(`Failed to fetch character data: ${response.statusText}`);
      }

      const characters: CharacterData[] = await response.json();
      const playerCharacter = characters.find(char => char.name) || characters[0];

      if (!playerCharacter) {
        setInventory([]);
        setGold(0);
        setLastUpdated(new Date());
        return;
      }

      const allItems: InventoryItem[] = [];

      if (playerCharacter.equipment) {
        Object.entries(playerCharacter.equipment).forEach(([itemName, quantity]) => {
          allItems.push({
            name: itemName,
            quantity,
            type: getItemType(itemName),
            description: getItemDescription(itemName),
            weight: getItemWeight(itemName)
          });
        });
      }

      if (playerCharacter.inventory_items) {
        Object.entries(playerCharacter.inventory_items).forEach(([itemName, quantity]) => {
          allItems.push({
            name: itemName,
            quantity,
            type: getItemType(itemName),
            description: getItemDescription(itemName),
            weight: getItemWeight(itemName)
          });
        });
      }

      setInventory(allItems);

      const detailResponse = await fetch(buildApiUrl(`/characters/id/${encodeURIComponent(playerCharacter.id)}`));
      if (detailResponse.ok) {
        const characterDetail = await detailResponse.json();
        setGold(characterDetail.gold ?? 0);
      } else {
        setGold(playerCharacter.gold ?? 0);
      }

      setLastUpdated(new Date());
    } catch (err) {
      const errMessage = err instanceof Error ? err.message : "An unknown error occurred.";
      setError(errMessage);
      console.error("Error loading inventory:", err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleRefresh = () => {
    loadInventory();
  };

  useEffect(() => {
    loadInventory();
  }, [loadInventory, refreshToken]);


  const getItemIcon = (type: string) => {
    switch (type) {
      case "weapon":
        return <Sword className="h-4 w-4" />;
      case "armor":
        return <Shield className="h-4 w-4" />;
      case "potion":
        return <FlaskConical className="h-4 w-4" />;
      case "scroll":
        return <ScrollText className="h-4 w-4" />;
      case "currency":
        return <Coins className="h-4 w-4" />;
      default:
        return <Package className="h-4 w-4" />;
    }
  };

  const getItemTypeColor = (type: string) => {
    switch (type) {
      case "weapon":
        return "bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300 border-red-200 dark:border-red-800";
      case "armor":
        return "bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-800";
      case "potion":
        return "bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300 border-green-200 dark:border-green-800";
      case "scroll":
        return "bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-300 border-purple-200 dark:border-purple-800";
      case "currency":
        return "bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800";
      default:
        return "bg-gray-100 dark:bg-gray-900/20 text-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-800";
    }
  };
  if (loading) {
    return (
      <div className="w-full bg-card rounded-lg border shadow-sm p-4">
        <div className="flex items-center gap-2 mb-4">
          <Package className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Inventory</h3>
        </div>
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full bg-card rounded-lg border shadow-sm p-4">
        <div className="flex items-center gap-2 mb-4">
          <Package className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Inventory</h3>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }


  return (
    <div className="w-full bg-card rounded-lg border shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Package className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Inventory</h3>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Coins className="h-4 w-4 text-yellow-600" />
            <span>{gold} GP</span>
          </div>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-1.5 rounded-md hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Refresh inventory"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {inventory.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-4">
          Inventory is empty
        </p>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {inventory.map((item, index) => (
            <div
              key={`${item.name}-${index}`}
              className="p-3 border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1">
                  <div className={`p-2 rounded-lg ${getItemTypeColor(item.type)}`}>
                    {getItemIcon(item.type)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-sm">{item.name}</h4>
                      {item.quantity > 1 && (
                        <span className="text-xs bg-muted text-muted-foreground px-1.5 py-0.5 rounded">
                          x{item.quantity}
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {item.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 pt-4 border-t">
        <div className="grid grid-cols-2 gap-4 text-xs mb-2">
          <div>
            <span className="text-muted-foreground">Item Count:</span>
            <div className="font-medium">{inventory.length}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Gold:</span>
            <div className="font-medium">{gold} GP</div>
          </div>
        </div>
        {/* Removed Last updated line, relies on parent component to trigger refresh */}
      </div>
    </div>
  );
}
