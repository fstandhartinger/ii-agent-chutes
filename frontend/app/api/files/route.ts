import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { path: dirPath } = await request.json();
    if (!dirPath) {
      return NextResponse.json({ error: "Path is required" }, { status: 400 });
    }

    // Extract workspace ID from the path
    const workspaceId = dirPath.split("/").pop();
    if (!workspaceId) {
      return NextResponse.json({ error: "Invalid workspace path" }, { status: 400 });
    }

    // Call the backend API to get file structure
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/files/list`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        workspace_id: workspaceId,
        path: "/var/data"
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json({ files: data.files || [] });
  } catch (error) {
    console.error("Error reading directory:", error);
    return NextResponse.json(
      { error: "Failed to read directory" },
      { status: 500 }
    );
  }
}
