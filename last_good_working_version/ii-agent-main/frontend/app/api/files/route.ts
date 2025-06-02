import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { path: dirPath } = await request.json();
    if (!dirPath) {
      return NextResponse.json({ error: "Path is required" }, { status: 400 });
    }

    // Normalize path to handle both Windows and Unix style paths
    const normalizedPath = dirPath.replace(/\\/g, "/");
    
    // Extract workspace ID from the path - remove trailing slashes first
    const cleanPath = normalizedPath.replace(/\/*$/, "");
    const pathParts = cleanPath.split("/");
    const workspaceId = pathParts[pathParts.length - 1];
    
    if (!workspaceId) {
      return NextResponse.json({ error: "Invalid workspace path" }, { status: 400 });
    }

    console.log(`Loading files for workspace: ${workspaceId} from path: ${normalizedPath}`);

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
      console.error(`Backend API error: ${response.status} ${response.statusText}`);
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`Received file list with ${data.files?.length || 0} items`);
    return NextResponse.json({ files: data.files || [] });
  } catch (error) {
    console.error("Error reading directory:", error);
    return NextResponse.json(
      { error: "Failed to read directory" },
      { status: 500 }
    );
  }
}
