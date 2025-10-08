/* globals $ */

const pinyinVideos = [
  {
    lessonId: '5f9c5385c32d410f1447c146',
    title: 'What Is Pinyin',
    filename: 'what-is-pinyin',
    intro:
      "Have you ever wondered how people type Chinese characters? The answer lies in the wonderfully useful phonetic system used to spell out Chinese words called 'pinyin'. In this lesson, get an introduction to pinyin and how you'll use it to start learning Chinese.",
    originalId: 'MTQxMTAxNA==',
    duration: '4:04',
    counts: { Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c147',
    duration: '3:46',
    title: 'An Introduction to the Tones',
    filename: 'introduction-to-the-tones',
    intro:
      "Chinese is a 'tonal language' - but what does that mean? In this lesson, listen as Yangyang explains how tones work in Chinese and why they're so important to mastering the language.",
    originalId: 'MTQxMTAyNQ==',
    counts: { Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c148',
    duration: '6:25',
    title: 'The 1st and 2nd Tones',
    filename: 'the-1st-and-2nd-tones',
    intro:
      "All of the tones are important, but it's a good idea to really focus on each one when you're getting started. In this lesson, learn all about the first and second tones, how to pronounce them, and a few tricks you can use to make sure your understanding and pronunciation of the first two tones is spot on.",
    originalId: 'MTQxMTAzNA==',
    counts: { Pinyin: 8, Audio: '2:08', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c149',
    duration: '3:54',
    title: 'The 3rd and 4th Tones',
    filename: 'the-3rd-and-4th-tones',
    intro:
      "You're halfway there with the tones now and it's time to tackle the third and fourth tones. In this lesson, let Yangyang break down these essential sounds for you and how to produce them yourself using a few essential tips.",
    originalId: 'MTQxMTAzNQ==',
    counts: { Pinyin: 8, Audio: '3:46', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c14d',
    duration: '3:28',
    title: 'Tone Changes and the Neutral Tone',
    filename: 'tone-changes-and-the-neutral-tone',
    intro:
      "Each word has a tone, but did you know that tones also change sometimes depending on context? It sounds tricky, but don't despair - watch this video as Yangyang breaks down the tone change rules for you as well as introducing the 5th 'neutral' tone.",
    originalId: 'MTQxMTAzNg==',
    counts: { Pinyin: 4, Audio: '3:01', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c155',
    duration: '5:34',
    title: 'Pinyin Finals - Part 1',
    filename: 'pinyin-finals-part-1',
    intro:
      "Pinyin finals are an essential part of mastering Chinese pronunciation. In this lesson, get started practicing finals by focusing on the first group of finals starting with the letter 'a'.",
    originalId: 'MTQxMTAxNQ==',
    counts: { Pinyin: 16, Audio: '3:24', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c156',
    duration: '3:55',
    title: 'Pinyin Finals - Part 2',
    filename: 'pinyin-finals-part-2',
    intro:
      "In this lesson, continue learning all of the possible pinyin finals group by group - this time jumping into the finals starting with the letter 'e'.",
    originalId: 'MTQxMTAxNg==',
    counts: { Pinyin: 21, Audio: '3:35', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c157',
    duration: '6:56',
    title: 'Pinyin Finals - Part 3',
    filename: 'pinyin-finals-part-3',
    intro:
      "In the next lesson of the pinyin finals series, learn all about the first section of the finals that start with the letter 'i'. This group can be a little tricky so make sure to pay attention and practice!",
    originalId: 'MTQxMTAxNw==',
    counts: { Pinyin: 23, Audio: '2:52', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c158',
    duration: '5:12',
    title: 'Pinyin Finals - Part 4',
    filename: 'pinyin-finals-part-4',
    intro:
      "In this lesson, finish up the group of finals you started in the last lesson - the finals that start with the letter 'i'. Make sure you watch all the way to the end to learn an essential spelling rule associated with this group.",
    originalId: 'MTQxMTAxOA==',
    counts: { Pinyin: 20, Audio: '3:44', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c15b',
    duration: '3:28',
    title: 'Pinyin Finals - Part 5',
    filename: 'pinyin-finals-part-5',
    intro:
      "In this lesson, continue learning the pinyin finals and focus on the finals that start with the letter 'o'. There are only three so listen close and make sure you don't miss any!",
    originalId: 'MTQxMTAxOQ==',
    counts: { Pinyin: 12, Audio: '2:43', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c15c',
    duration: '4:22',
    title: 'Pinyin Finals - Part 6',
    filename: 'pinyin-finals-part-6',
    intro:
      "In this lesson, get started learning the first section of the 'u' finals in pinyin. 'U' might not be pronounced as you think, so make sure you pay close attention. You'll learn new pieces of vocab and practice your tones while you're at it!",
    originalId: 'MTQxMTAyMA==',
    counts: { Pinyin: 26, Audio: '3:44', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c15d',
    duration: '5:14',
    title: 'Pinyin Finals - Part 7',
    filename: 'pinyin-finals-part-7',
    intro:
      "In part seven of the pinyin final series, continue learning the rest of the finals that start with the letter 'u'. You'll also learn an important tip about a few cases where the 'u' doesn't appear, but is pronounced anyway.",
    originalId: 'MTQxMTAyMQ==',
    counts: { Pinyin: 16, Audio: '3:02', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c15e',
    duration: '6:05',
    title: 'The Pinyin Letter Ü',
    filename: 'The+Pinyin+Letter+u%CC%88',
    intro:
      'Many sounds in Chinese already exist in English, but some of the new ones can be tricky for English speakers. In this lesson, take a short break from finals and focus on the special pinyin final ü and how to pronounce it.',
    originalId: 'MTQxMTAyMg==',
    counts: { Audio: '1:19', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c15f',
    duration: '5:03',
    title: 'Pinyin Finals - Part 8',
    filename: 'pinyin-finals-part-8',
    intro:
      "In this lesson, get ready to finish off your work on pinyin finals by focusing on all the finals that start with the letter 'ü'. The special spelling rules from the previous lesson apply here, so make sure to pay special attention!",
    originalId: 'MTQxMTAyMw==',
    counts: { Pinyin: 20, Audio: '3:53', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c162',
    duration: '4:32',
    title: 'Pinyin Initials - Part 1',
    filename: 'pinyin-initials-part-1',
    intro:
      "You've learned the Chinese finals, and now it's time to start learning 'initials'. Fortunately, most Chinese initial sounds are already found in English! So you can focus on the ones that matter. In this video, get started with 'j', 'q', and 'x'.",
    originalId: 'MTQxMTAyNA==',
    counts: { Pinyin: 17, Audio: '5:28', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c163',
    duration: '7:49',
    title: 'Pinyin Initials - Part 2',
    filename: 'pinyin-initials-part-2',
    intro:
      "In this lesson, continue your study of Chinese initials with four new sounds: 'zh', 'ch', 'sh', and 'r'. Remember, these sounds are not found in English so make sure to pay close attention to the explanations and practice yourself!",
    originalId: 'MTQxMTAyNg==',
    counts: { Pinyin: 20, Audio: '6:37', Quiz: 10 },
  },
  {
    lessonId: '5f9c5385c32d410f1447c164',
    duration: '6:00',
    title: 'Pinyin Initials - Part 3',
    filename: 'pinyin-initials-part-3',
    intro:
      "In your final lesson on Chinese initials, learn the 'z', 'c', and 's' sounds to close out your mastery of Chinese pronunciation! Once again, remember to pay close attention how to form these sounds with your mouth as they may not come as easily as other Chinese sounds.",
    originalId: 'MTQxMTAyNw==',
    counts: { Pinyin: 14, Audio: '6:28', Quiz: 10 },
  },
];

window.addEventListener('load', function () {
  function createdPlayer(mediaList, el) {
    var indexHtml = [];
    mediaList.forEach(({ title, filename, duration }, index) => {
      indexHtml.push(`<li data-index="${index}"> 
              <img src="https://cdn.yoyochinese.com/images/webpage/front/thumbnails/${filename}.jpg">
              <div>
                <div class="title">${title}</div>
                <div class="duration">${duration}</div>
              </div>
            </li>`);
    });
    el.find('.video-list-index').html(indexHtml.join(''));
    el.find('.video-list-index').on('click', 'li', function (e) {
      el.find('li.active').removeClass('active');
      $(e.currentTarget).addClass('active');
      playVideo(mediaList[$(e.currentTarget).data().index], el);
      $(document.scrollingElement).animate({
        scrollTop:
          document.scrollingElement.scrollTop +
          el.find('.main-iframe')[0].getBoundingClientRect().top -
          120,
      });
    });
  }

  function playVideo(
    { title, intro, filename, originalId, counts, lessonId },
    el,
  ) {
    const baseUri = 'https://video.yoyochinese.com/s/pinyin/' + filename;
    el.find('.main-iframe').replaceWith(
      '<video' +
        ' class="main-iframe"' +
        ' disablepictureinpicture' +
        ' preload="none"' +
        ' crossorigin="anonymous"' +
        ' playsinline' +
        ' controls' +
        ' controlsList="nodownload"' +
        ' poster="' +
        'https://cdn.yoyochinese.com/thumbnails/' +
        originalId +
        '.webp"' +
        '>' +
        '<source src="' +
        baseUri +
        '.mp4" type="video/mp4" />' +
        '<source src="' +
        baseUri +
        '.webm" type="video/webm" />' +
        '</video>',
    );
    el.find('.video-title').html(title);
    el.find('.video-info').html(intro);
    var countli = counts
      ? Object.keys(counts).map((c) => {
          return `<li class='${c}'><span>${c}</span>${counts[c]}</li>`;
        })
      : [];
    el.find('.count-list').html(countli.join(''));

    if (
      counts &&
      (counts.Pinyin || counts.Flashcards || counts.Audio || counts.Dialogue)
    ) {
      el.find('.media-count').show();
      el.find('.practice-link')
        .attr('href', '/auth/sign-up?returnType=practice&returnId=' + lessonId)
        .show();
      el.find('.quiz-link')
        .addClass('yy-button yy-button--primary yy-button--text')
        .html('Skip to Quiz');
    } else if (counts && counts.Quiz) {
      el.find('.media-count').show();
      el.find('.practice-link').hide();
      el.find('.quiz-link')
        .removeClass('yy-button yy-button--primary yy-button--text')
        .html(
          '<button class="yy-button yy-button--primary yy-button--small">Start Quiz</button>',
        );
    } else {
      el.find('.media-count').hide();
    }

    if (counts && counts.Quiz) {
      el.find('.quiz-link')
        .attr('href', '/auth/sign-up?returnType=quiz&returnId=' + lessonId)
        .show();
    } else {
      el.find('.quiz-link').hide();
    }
  }

  function registEvent() {
    var navs = $('.tabs-nav.active');
    var bar = $('.tabs-bar');
    bar.width(navs[0].offsetWidth);
    bar.css('left', navs[0].offsetLeft + 'px');
  }
  createdPlayer(pinyinVideos, $('.pinyin.video-player-list'));
  playVideo(pinyinVideos[0], $('.pinyin.video-player-list'));

  registEvent();
});
