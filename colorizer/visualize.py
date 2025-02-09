from fastai.core import *
from fastai.vision import *
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from .filters import IFilter, MasterFilter, ColorizerFilter
from .generators import gen_inference_deep, gen_inference_wide
from tensorboardX import SummaryWriter
from scipy import misc
from PIL import Image
import ffmpeg
import youtube_dl
import gc
import requests
from io import BytesIO
import base64
from IPython import display as ipythondisplay
from IPython.display import HTML
from IPython.display import Image as ipythonimage


class ModelImageVisualizer:
    def __init__(self, filter: IFilter, results_dir: str = None):
        self.filter = filter
        self.results_dir = None if results_dir is None else Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _clean_mem(self):
        torch.cuda.empty_cache()
        # gc.collect()

    def _open_pil_image(self, path: Path) -> Image:
        return PIL.Image.open(path).convert("RGB")

    def _get_image_from_url(self, url: str) -> Image:
        response = requests.get(url, timeout=30)
        img = PIL.Image.open(BytesIO(response.content)).convert("RGB")
        return img

    def plot_transformed_image_from_url(
        self,
        url: str,
        path: str = "test_images/image.png",
        figsize: (int, int) = (20, 20),
        render_factor: int = None,
        display_render_factor: bool = False,
        compare: bool = False,
    ) -> Path:
        img = self._get_image_from_url(url)
        img.save(path)
        return self.plot_transformed_image(
            path=path,
            figsize=figsize,
            render_factor=render_factor,
            display_render_factor=display_render_factor,
            compare=compare,
        )

    def plot_transformed_image(
        self,
        path: str,
        figsize: (int, int) = (20, 20),
        render_factor: int = None,
        display_render_factor: bool = False,
        compare: bool = False,
    ) -> Path:
        path = Path(path)
        result = self.get_transformed_image(path, render_factor)
        orig = self._open_pil_image(path)
        if compare:
            self._plot_comparison(
                figsize, render_factor, display_render_factor, orig, result
            )
        else:
            self._plot_solo(figsize, render_factor, display_render_factor, result)

        return self._save_result_image(path, result)

    def _plot_comparison(
        self,
        figsize: (int, int),
        render_factor: int,
        display_render_factor: bool,
        orig: Image,
        result: Image,
    ):
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        self._plot_image(
            orig,
            axes=axes[0],
            figsize=figsize,
            render_factor=render_factor,
            display_render_factor=False,
        )
        self._plot_image(
            result,
            axes=axes[1],
            figsize=figsize,
            render_factor=render_factor,
            display_render_factor=display_render_factor,
        )

    def _plot_solo(
        self,
        figsize: (int, int),
        render_factor: int,
        display_render_factor: bool,
        result: Image,
    ):
        fig, axes = plt.subplots(1, 1, figsize=figsize)
        self._plot_image(
            result,
            axes=axes,
            figsize=figsize,
            render_factor=render_factor,
            display_render_factor=display_render_factor,
        )

    def _save_result_image(self, source_path: Path, image: Image) -> Path:
        result_path = self.results_dir / source_path.name
        image.save(result_path)
        return result_path

    def get_transformed_image(self, path: Path, render_factor: int = None) -> Image:
        self._clean_mem()
        orig_image = self._open_pil_image(path)
        filtered_image = self.filter.filter(
            orig_image, orig_image, render_factor=render_factor
        )
        return filtered_image

    def _plot_image(
        self,
        image: Image,
        render_factor: int,
        axes: Axes = None,
        figsize=(20, 20),
        display_render_factor: bool = False,
    ):
        if axes is None:
            _, axes = plt.subplots(figsize=figsize)
        axes.imshow(np.asarray(image) / 255)
        axes.axis("off")
        if render_factor is not None and display_render_factor:
            plt.text(
                10,
                10,
                "render_factor: " + str(render_factor),
                color="white",
                backgroundcolor="black",
            )

    def _get_num_rows_columns(self, num_images: int, max_columns: int) -> (int, int):
        columns = min(num_images, max_columns)
        rows = num_images // columns
        rows = rows if rows * columns == num_images else rows + 1
        return rows, columns


def get_image_colorizer(
    render_factor: int = 35, artistic: bool = True
) -> ModelImageVisualizer:
    if artistic:
        return get_artistic_image_colorizer(render_factor=render_factor)
    else:
        return get_stable_image_colorizer(render_factor=render_factor)


def get_stable_image_colorizer(
    root_folder: Path = Path("./"),
    weights_name: str = "ColorizeStable_gen",
    results_dir="result_images",
    render_factor: int = 35,
) -> ModelImageVisualizer:
    learn = gen_inference_wide(root_folder=root_folder, weights_name=weights_name)
    filtr = MasterFilter([ColorizerFilter(learn=learn)], render_factor=render_factor)
    vis = ModelImageVisualizer(filtr, results_dir=results_dir)
    return vis


def get_artistic_image_colorizer(
    root_folder: Path = Path("./"),
    weights_name: str = "ColorizeArtistic_gen",
    results_dir="result_images",
    render_factor: int = 35,
) -> ModelImageVisualizer:
    learn = gen_inference_deep(root_folder=root_folder, weights_name=weights_name)
    filtr = MasterFilter([ColorizerFilter(learn=learn)], render_factor=render_factor)
    vis = ModelImageVisualizer(filtr, results_dir=results_dir)
    return vis


def show_image_in_notebook(image_path: Path):
    ipythondisplay.display(ipythonimage(str(image_path)))
