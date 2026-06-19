document.addEventListener("DOMContentLoaded", function () {
  if (!window.QRCode) {
    return;
  }

  document.querySelectorAll(".qrcode-block").forEach(function (block) {
    var data = block.querySelector(".qrcode-data");
    var output = block.querySelector(".qrcode-output");

    if (!data || !output) {
      return;
    }

    var text = "";
    try {
      text = JSON.parse(data.textContent);
    } catch (error) {
      text = data.textContent;
    }

    output.innerHTML = "";
    new QRCode(output, {
      text: text,
      width: 192,
      height: 192,
      correctLevel: QRCode.CorrectLevel.M
    });
  });
});
