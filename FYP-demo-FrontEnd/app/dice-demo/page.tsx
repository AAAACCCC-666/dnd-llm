"use client"

import { DiceRoller, type DiceRollResult } from "@/components/chat/dice-roller";

export default function DiceDemoPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-8">
      <div className="container mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🎲 D&D 5e Dice Roller Demo
          </h1>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Experience the interactive 3D dice roller with D&D 5e racial bonuses.
            Perfect for character creation and gameplay!
          </p>
        </div>

        <DiceRoller
          onRollComplete={(result: DiceRollResult) => {
            console.log("Dice roll completed:", result);
          }}
        />

        <div className="mt-12 max-w-4xl mx-auto">
          <div className="bg-white/80 rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Features</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h3 className="font-semibold text-gray-800">🎯 Core Features</h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• 3D animated dice with realistic physics</li>
                  <li>• D&D 5e standard 4d6 drop lowest method</li>
                  <li>• Secure random number generation</li>
                  <li>• Real-time race bonus calculations</li>
                </ul>
              </div>
              <div className="space-y-3">
                <h3 className="font-semibold text-gray-800">🧝 Racial Bonuses</h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li>• All PHB races supported</li>
                  <li>• Special Half-Elf +2 CHA +1 to two others</li>
                  <li>• Automatic bonus application</li>
                  <li>• Real-time result calculation</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
