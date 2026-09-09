import React, { useState } from 'react'

export default function Antigravity() {
  const [enabled, setEnabled] = useState(false)
  const [intensity, setIntensity] = useState(50)

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-3xl w-full bg-white shadow-md rounded-lg p-8">
        <h1 className="text-2xl font-semibold mb-4">Antigravity View</h1>
        <p className="text-sm text-gray-600 mb-6">Interactive antigravity visualization placeholder.</p>

        <div className="mb-4">
          <label className="flex items-center space-x-3">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="h-5 w-5"
            />
            <span className="ml-2">Enable Antigravity</span>
          </label>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Intensity: {intensity}%</label>
          <input
            type="range"
            min="0"
            max="100"
            value={intensity}
            onChange={(e) => setIntensity(e.target.value)}
            className="w-full"
          />
        </div>

        <div className="border rounded p-4 text-sm text-gray-700">
          <div className="font-semibold mb-2">Simulation</div>
          {enabled ? (
            <div>Antigravity enabled at intensity {intensity}% — visualization would render here.</div>
          ) : (
            <div>Antigravity is disabled. Toggle the checkbox to enable the view.</div>
          )}
        </div>
      </div>
    </div>
  )
}
