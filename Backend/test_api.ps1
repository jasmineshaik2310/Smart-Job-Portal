# test_api_fixed.ps1
$baseUrl = "http://localhost:8000"

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Testing SmartJob Portal API" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# First check if server is running
Write-Host "`n[0] Checking server health..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -UseBasicParsing
    if ($healthResponse.StatusCode -eq 200) {
        Write-Host "✅ Server is running!" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Server is not running! Please start the server first:" -ForegroundColor Red
    Write-Host "   uvicorn main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
    exit
}

# Test 1: Login with correct format
Write-Host "`n[1] Testing Login..." -ForegroundColor Yellow

# Create the body as a string
$body = "email=jobseeker@demo.com&password=demo123"

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/login" `
        -Method POST `
        -ContentType "application/x-www-form-urlencoded" `
        -Body $body `
        -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        $token = $data.access_token
        Write-Host "✅ Login successful!" -ForegroundColor Green
        Write-Host "   User: $($data.user.first_name) $($data.user.last_name)" -ForegroundColor Gray
        Write-Host "   Token: $($token.Substring(0, 50))..." -ForegroundColor Gray
    } else {
        Write-Host "❌ Login failed with status: $($response.StatusCode)" -ForegroundColor Red
        Write-Host "   Response: $($response.Content)" -ForegroundColor Red
        exit
    }
} catch {
    Write-Host "❌ Login failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $reader.DiscardBufferedData()
        $responseBody = $reader.ReadToEnd()
        Write-Host "   Response: $responseBody" -ForegroundColor Red
    }
    exit
}

# Test 2: Get all jobs
Write-Host "`n[2] Getting all jobs..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/jobs" -Method GET -UseBasicParsing
    $jobs = $response.Content | ConvertFrom-Json
    Write-Host "✅ Found $($jobs.jobs.Count) jobs" -ForegroundColor Green
    foreach ($job in $jobs.jobs | Select-Object -First 3) {
        Write-Host "   - $($job.title) at $($job.company)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed to get jobs: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Get profile
Write-Host "`n[3] Getting user profile..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/profile?token=$token" -Method GET -UseBasicParsing
    $profile = $response.Content | ConvertFrom-Json
    Write-Host "✅ Profile retrieved!" -ForegroundColor Green
    Write-Host "   Name: $($profile.first_name) $($profile.last_name)" -ForegroundColor Gray
    Write-Host "   Email: $($profile.email)" -ForegroundColor Gray
    Write-Host "   Type: $($profile.user_type)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Failed to get profile: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Get job matches
Write-Host "`n[4] Getting job matches..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/jobs/matches?token=$token" -Method GET -UseBasicParsing
    $matches = $response.Content | ConvertFrom-Json
    Write-Host "✅ Found $($matches.total) job matches" -ForegroundColor Green
    foreach ($match in $matches.matches | Select-Object -First 3) {
        Write-Host "   - $($match.title) - $($match.match_score)% match" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed to get matches: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Upload a test resume
Write-Host "`n[5] Uploading test resume..." -ForegroundColor Yellow

# Create a test resume file
$resumeContent = @"
Alex Johnson
Senior Python Developer

SUMMARY
Experienced Python developer with 5+ years in machine learning and AI applications.

SKILLS
- Python, Django, Flask
- Machine Learning, TensorFlow, PyTorch
- SQL, PostgreSQL, MongoDB
- AWS, Docker, Kubernetes
- React, JavaScript

EXPERIENCE
Senior AI Engineer | TechCorp | 2021-Present
- Led development of computer vision models
- Improved model accuracy by 25%
- Deployed ML models to production

Machine Learning Engineer | DataStartup | 2019-2021
- Built predictive models for customer analytics
- Implemented NLP solutions for text classification

EDUCATION
MSc in Computer Science | Stanford University | 2019
BSc in Computer Science | UC Berkeley | 2017
"@

$resumeFile = "test_resume.txt"
$resumeContent | Out-File -FilePath $resumeFile -Encoding UTF8

try {
    # Use multipart/form-data for file upload
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    
    $bodyLines = @(
        "--$boundary",
        "Content-Disposition: form-data; name=`"token`"$LF",
        "$token",
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"test_resume.txt`"",
        "Content-Type: text/plain$LF",
        $resumeContent,
        "--$boundary--$LF"
    )
    
    $body = [string]::Join($LF, $bodyLines)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    
    $headers = @{
        "Content-Type" = "multipart/form-data; boundary=$boundary"
    }
    
    $response = Invoke-WebRequest -Uri "$baseUrl/api/resume/upload" `
        -Method POST `
        -Headers $headers `
        -Body $bytes `
        -UseBasicParsing
    
    $result = $response.Content | ConvertFrom-Json
    Write-Host "✅ Resume uploaded successfully!" -ForegroundColor Green
    Write-Host "   Skills extracted: $($result.extracted_skills -join ', ')" -ForegroundColor Gray
    Write-Host "   Skills count: $($result.skills_count)" -ForegroundColor Gray
    Write-Host "   Resume score: $($result.resume_score)" -ForegroundColor Gray
    Write-Host "   Job matches found: $($result.total_matches)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Failed to upload resume: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $reader.DiscardBufferedData()
        $responseBody = $reader.ReadToEnd()
        Write-Host "   Response: $responseBody" -ForegroundColor Red
    }
}

# Clean up
Remove-Item $resumeFile -ErrorAction SilentlyContinue

# Test 6: Get job seeker dashboard
Write-Host "`n[6] Getting job seeker dashboard..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/jobseeker/dashboard?token=$token" -Method GET -UseBasicParsing
    $dashboard = $response.Content | ConvertFrom-Json
    Write-Host "✅ Dashboard loaded!" -ForegroundColor Green
    Write-Host "   Welcome: $($dashboard.user.first_name) $($dashboard.user.last_name)" -ForegroundColor Gray
    Write-Host "   Resume Score: $($dashboard.stats.resume_score)" -ForegroundColor Gray
    Write-Host "   Applications: $($dashboard.stats.applications_count)" -ForegroundColor Gray
    Write-Host "   Job Matches: $($dashboard.stats.matches_count)" -ForegroundColor Gray
    Write-Host "   Skills Count: $($dashboard.stats.skills_count)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Failed to get dashboard: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "✅ API testing completed!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan