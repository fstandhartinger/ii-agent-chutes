import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { path } = await request.json();
    if (!path) {
      return NextResponse.json({ error: "Path is required" }, { status: 400 });
    }

    // Extract workspace ID from the path
    const pathParts = path.split("/");
    const workspaceIndex = pathParts.findIndex((part: string) => part === "workspace");
    if (workspaceIndex === -1 || workspaceIndex + 1 >= pathParts.length) {
      return NextResponse.json({ error: "Invalid workspace path" }, { status: 400 });
    }
    
    const workspaceId = pathParts[workspaceIndex + 1];
    const relativePath = pathParts.slice(workspaceIndex + 2).join("/");

    // Call the backend API to get file content
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/files/content`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        workspace_id: workspaceId,
        path: relativePath
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json({ content: data.content || "" });
  } catch (error) {
    console.error("Error reading file:", error);
    return NextResponse.json({ error: "Failed to read file" }, { status: 500 });
  }
}
