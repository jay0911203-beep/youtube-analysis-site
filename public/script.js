// 페이지 로딩 시 트렌드 키워드 가져오기
document.addEventListener('DOMContentLoaded', () => {
    console.log("페이지 로딩 완료. 트렌드 키워드 가져오기를 시작합니다.");
    fetchTrendingKeywords('KR', document.querySelector('#trends-kr ol'), document.querySelector('#trends-kr .loader'));
    fetchTrendingKeywords('US', document.querySelector('#trends-us ol'), document.querySelector('#trends-us .loader'));
    fetchTrendingKeywords('JP', document.querySelector('#trends-jp ol'), document.querySelector('#trends-jp .loader'));
});

async function fetchTrendingKeywords(geo, listElement, loaderElement) {
    const url = `/api/trending-keywords?geo=${geo}`;
    console.log(`[트렌드] ${geo} 국가 데이터 요청: ${url}`);
    try {
        const response = await fetch(url);
        // 서버 응답이 성공적인지 확인 (오류 코드 포함)
        if (!response.ok) {
            throw new Error(`서버 응답 오류: ${response.status} ${response.statusText}`);
        }
        const keywords = await response.json();

        // 서버에서 보낸 데이터가 'error' 키를 포함하는지 확인
        if (keywords.error) {
            throw new Error(`서버에서 오류를 반환했습니다: ${keywords.error}`);
        }

        console.log(`[트렌드] ${geo} 국가 데이터 수신 성공:`, keywords);
        loaderElement.style.display = 'none';
        keywords.forEach(keyword => {
            const li = document.createElement('li');
            li.textContent = keyword;
            listElement.appendChild(li);
        });
    } catch (error) {
        // 오류 발생 시 브라우저 콘솔에 상세 내용 출력
        console.error(`[트렌드] ${geo} 국가 데이터를 가져오는 중 심각한 오류 발생:`, error);
        loaderElement.textContent = '불러오기 실패';
    }
}

// 검색 버튼 클릭 이벤트
document.getElementById('search-btn').addEventListener('click', performSearch);

// 검색 기능 함수
async function performSearch() {
    const keyword = document.getElementById('keyword').value;
    const period = document.getElementById('period').value;
    const resultsSection = document.getElementById('results-section');
    const loadingDiv = document.getElementById('loading');
    const longFormDiv = document.getElementById('long-form');
    const shortsDiv = document.getElementById('shorts');

    if (!keyword) { alert('검색어를 입력해주세요.'); return; }

    resultsSection.classList.remove('hidden');
    longFormDiv.innerHTML = '';
    shortsDiv.innerHTML = '';
    loadingDiv.classList.remove('hidden');

    const url = `/api/search?keyword=${encodeURIComponent(keyword)}&period=${period}`;
    console.log(`[검색] 데이터 요청: ${url}`);

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`서버 응답 오류: ${response.status} ${response.statusText}`);
        }
        const videos = await response.json();

        if (videos.error) {
            throw new Error(`서버에서 오류를 반환했습니다: ${videos.error}`);
        }
        
        console.log(`[검색] 데이터 수신 성공:`, videos);
        loadingDiv.classList.add('hidden');
        
        const longFormVideos = videos.filter(v => !v.isShort);
        const shortsVideos = videos.filter(v => v.isShort);

        populateResults(longFormVideos, longFormDiv, '롱폼 영상이 없습니다.');
        populateResults(shortsVideos, shortsDiv, '숏폼 영상이 없습니다.');

    } catch (error) {
        console.error('[검색] 데이터를 가져오는 중 심각한 오류 발생:', error);
        loadingDiv.classList.add('hidden');
        longFormDiv.innerHTML = `<p>오류 발생: ${error.message}</p>`;
    }
}

// 결과를 화면에 채우는 함수
function populateResults(videoArray, element, emptyMessage) {
    if (videoArray.length === 0) {
        element.innerHTML = `<p>${emptyMessage}</p>`;
        return;
    }
    videoArray.forEach(video => {
        const subscriberText = video.subscriberCount === '비공개' 
            ? '구독자: 비공개' 
            : `구독자: ${Number(video.subscriberCount).toLocaleString()}명`;
        
        const videoElement = document.createElement('div');
        videoElement.classList.add('video-item');
        videoElement.innerHTML = `
            <div class="thumbnail">
                <a href="https://www.youtube.com/watch?v=${video.id}" target="_blank">
                    <img src="${video.thumbnail}" alt="${video.title}">
                </a>
            </div>
            <div class="info">
                <h3>${video.title}</h3>
                <p>${video.channelTitle}</p>
                <p class="views">조회수: ${Number(video.viewCount).toLocaleString()}회</p>
                <p class="subs">${subscriberText}</p>
                <p class="channel-date">채널 개설일: ${video.channelPublishedAt}</p>
            </div>
        `;
        element.appendChild(videoElement);
    });
}

// 탭 기능 구현 (기존과 동일)
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        button.classList.add('active');
        document.getElementById(button.dataset.tab).classList.add('active');
    });
});