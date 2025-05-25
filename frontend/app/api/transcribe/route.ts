import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { audio_b64 } = await request.json();

    if (!audio_b64) {
      return NextResponse.json({ error: 'Audio data is required' }, { status: 400 });
    }

    // Use CHUTES API to transcribe audio
    const apiToken = process.env.CHUTES_API_TOKEN;
    
    if (!apiToken) {
      return NextResponse.json({ error: 'CHUTES API token not configured' }, { status: 500 });
    }

    const response = await fetch('https://chutes-whisper-large-v3.chutes.ai/transcribe', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        language: null,
        audio_b64: audio_b64,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      const transcription = data[0]?.data || '';
      return NextResponse.json({ transcription });
    } else {
      console.error('CHUTES transcription failed:', response.statusText);
      return NextResponse.json({ error: 'Transcription failed' }, { status: 500 });
    }
  } catch (error) {
    console.error('Error in transcription API:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
} 