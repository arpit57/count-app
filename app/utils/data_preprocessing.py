import os
import cv2
# import numpy as np
# from ultralytics import YOLO


# from enlighten_inference import EnlightenOnnxModel


class Preprocess:
    """The module is the preprocessing pipeline which includes masking, auto brigthness and sharpness, enligthen.
    The module takes the input path of the image.
    Multiple images and folder intake in under process."""

    def __init__(self, path):
        """
        Initialize the preprocess class with the provided path.

        Parameters:
            path (str): The path to the directory containing the input images.

        Returns:
            None
        """
        super(Preprocess, self).__init__()
       
        self.path = path
        self.r = (693, 0, 576, 903)
        self.sr = cv2.dnn_superres.DnnSuperResImpl_create()
        
        # Get the directory of the current script
        # script_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the model file
        # model_path = os.path.join(script_dir, "best.pt")

        # # Initialize the YOLO model with the correct path
        # self.model = YOLO(model_path)
        # self.model = YOLO("/home/arpit57/countApp/app/models/best.pt")

    def SuperResolution(self):
        """
        Loads an image to be super-resolved by the FSRCNN model and returns its upsampled version.
        The path of the model is read from the output of checkFolder() and the model is set to
        FSRCNN with a scale factor of 3.

        Returns:
            numpy.ndarray: The upsampled image.
        """

        self._path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FSRCNN_x3.pb")
        # self._path = r"/home/arpit57/countApp/app/models/FSRCNN_x3.pb"
        self.sr.readModel(self._path)
        self.sr.setModel("fsrcnn", 3)

        upsample = self.sr.upsample(self.denoise())

        return upsample

    def checkFolder(self):
        """
        Check if the required folders exist and create them if they don't.
        :return: A tuple containing the paths to the output, image, and model folders.
        """

        self.base_path = os.getcwd()
        self.img_path = os.path.join(self.base_path, "img")
        self.model_path = os.path.join(self.base_path, "models")
        self.output_path = os.path.join(self.base_path, "output_test")

        self.folder_list = [self.img_path, self.model_path, self.output_path]
        if not os.path.exists(self.output_path):
            os.mkdir(self.output_path)
        if not os.path.exists(self.model_path):
            os.mkdir(self.model_path)
        if not os.path.exists(self.img_path):
            os.mkdir(self.img_path)
        return self.output_path, self.img_path, self.model_path

    def loadImage(self):
        """
        Load an image from the given path using OpenCV.

        Returns:
            A numpy array representing the image.
        """
        # cv2.imshow("patgjjb ", self.path)
        # cv2.waitKey(0)
        return self.path

    # def segment(self):
    #     """
    #     Performs image segmentation on the loaded image using a pre-trained model.

    #     Returns:
    #     - new (numpy.ndarray): The segmented image.
    #     - ori_img (numpy.ndarray): The original image.
    #     """
    #     try:
    #         load_image = self.loadImage()

    #         self.results = self.model.predict(load_image, retina_masks=True)

    #         if self.results[0].masks is None:
    #             print("No Mask Found")
    #             return load_image, load_image, None
    #         for result in self.results:
    #             self.mask = result.masks.cpu().numpy()
    #             self.bbox = result.boxes[0].cpu().numpy()
    #             self.masks = self.mask.data.astype(bool)
    #             self.ori_img = result.orig_img

    #             for m in self.masks:
    #                 self.new = np.zeros_like(self.ori_img, dtype=np.uint8)

    #                 self.new[m] = self.ori_img[m]

    #         return self.new, self.ori_img, self.results[0].masks
    #     except Exception as error:
    #         print("error is  :", error)

    def denoise(self):
        # im, og, _ = self.segment()
       
        denosing = cv2.fastNlMeansDenoisingColored(self.loadImage(), None, 1, 1, 7, 21)
       

        return denosing
    
