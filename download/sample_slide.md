---
marp: true
---

<!-- スライド1 -->
# スライドのタイトル

<!-- スライド2 -->
## 10分のタイマー

<script>
<!--
// カウントダウンタイマーの設定
function startTimer(duration, display) {
  var timer = duration, minutes, seconds;
  setInterval(function () {
    minutes = parseInt(timer / 60, 10)
    seconds = parseInt(timer % 60, 10);

    minutes = minutes < 10 ? "0" + minutes : minutes;
    seconds = seconds < 10 ? "0" + seconds : seconds;

    display.textContent = minutes + ":" + seconds;

    if (--timer < 0) {
      timer = duration;
    }
  }, 1000);
}

window.onload = function () {
  var tenMinutes = 60 * 10,
      display = document.querySelector('#timer');
  startTimer(tenMinutes, display);
};
-->
</script>

<!-- スライド3 -->
## 残り時間: <span id="timer">10:00</span>

<!-- スライド4 -->
## おわり
