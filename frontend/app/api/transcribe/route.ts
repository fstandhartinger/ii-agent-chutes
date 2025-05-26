import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { audio_b64 } = await request.json();

    if (!audio_b64) {
      console.error('Transcription API: No audio data provided');
      return NextResponse.json({ error: 'Audio data is required' }, { status: 400 });
    }

    console.log('Transcription API: Received audio data, length:', audio_b64.length);

    // Use CHUTES API to transcribe audio - using CHUTES_API_KEY to match backend convention
    const apiToken = process.env.CHUTES_API_KEY;
    
    console.log('Transcription API: Checking for CHUTES_API_KEY...');
    if (!apiToken) {
      console.error('Transcription API: CHUTES_API_KEY environment variable not found');
      console.error('Available env vars:', Object.keys(process.env).filter(key => key.includes('CHUTES')));
      return NextResponse.json({ error: 'CHUTES API token not configured' }, { status: 500 });
    }

    console.log('Transcription API: Found API key, making request to Chutes...');
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

    console.log('Transcription API: Chutes response status:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('Transcription API: Chutes response data:', data);
      const transcription = data[0]?.data || '';
      console.log('Transcription API: Extracted transcription:', transcription);
      return NextResponse.json({ transcription });
    } else {
      const errorText = await response.text();
      console.error('CHUTES transcription failed:', response.status, response.statusText, errorText);
      return NextResponse.json({ error: 'Transcription failed' }, { status: 500 });
    }
  } catch (error) {
    console.error('Error in transcription API:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
} 