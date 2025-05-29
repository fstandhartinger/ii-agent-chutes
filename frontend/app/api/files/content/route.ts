import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { path } = await request.json();
    if (!path) {
      return NextResponse.json({ error: "Path is required" }, { status: 400 });
    }

    // Normalize path to handle both Windows and Unix style paths
    const normalizedPath = path.replace(/\\/g, "/");
    
    // Extract workspace ID from the path - remove trailing slashes first
    const cleanPath = normalizedPath.replace(/\/*$/, "");
    const pathParts = cleanPath.split("/");
    const workspaceId = pathParts[pathParts.length - 2]; // Second to last part is workspace ID
    const fileName = pathParts[pathParts.length - 1]; // Last part is file name
    
    if (!workspaceId || !fileName) {
      return NextResponse.json({ error: "Invalid file path" }, { status: 400 });
    }

    console.log(`Loading file content for workspace: ${workspaceId}, file: ${fileName}`);

    // Call the backend API to get file content
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/files/content`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        workspace_id: workspaceId,
        path: fileName
      }),
    });

    if (!response.ok) {
      console.error(`Backend API error: ${response.status} ${response.statusText}`);
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`Received file content, length: ${data.content?.length || 0}`);
    return NextResponse.json({ content: data.content || "" });
  } catch (error) {
    console.error("Error reading file:", error);
    return NextResponse.json(
      { error: "Failed to read file" },
      { status: 500 }
    );
  }
}
