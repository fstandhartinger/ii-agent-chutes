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

    // Call the backend API to download the zip
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/files/download-zip`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        workspace_id: workspaceId,
        path: `/var/data/${relativePath}`
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    // Get the filename from the response headers
    const contentDisposition = response.headers.get('content-disposition');
    let filename = 'download.zip';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }

    // Stream the zip content
    const zipBuffer = await response.arrayBuffer();
    
    return new NextResponse(zipBuffer, {
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error("Error downloading zip:", error);
    return NextResponse.json({ error: "Failed to download zip" }, { status: 500 });
  }
} 